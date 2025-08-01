import os
import logging
from dotenv import load_dotenv
from pyspark.sql import SparkSession
import firebase_admin
from firebase_admin import firestore, credentials

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger('load_to_firestore')

# Initialize Firebase Admin SDK with credentials.
try:
    firebase_credentials_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
    if not firebase_credentials_path:
        raise ValueError("FIREBASE_CREDENTIALS_PATH environment variable not set.")
    if not os.path.exists(firebase_credentials_path):
        raise FileNotFoundError(f"Firebase credentials file not found at: {firebase_credentials_path}")

    cred = credentials.Certificate(firebase_credentials_path)
    firebase_admin.initialize_app(cred)

    # Initialize Firestore client after the app is initialized
    db = firestore.client() 
except Exception as e:
    logging.error(f"Failed to initialize Firebase or Firestore client: {e}")

def main():
    logger.info("Starting load to Firestore process.")

    # Retrieve the path to the processed Parquet data from environment variables.
    data_processed_parquet = os.getenv('DATA_PROCESSED_PARQUET')
    if not data_processed_parquet:
        logger.error("DATA_PROCESSED_PARQUET environment variable not set. Exiting.")
        raise ValueError("DATA_PROCESSED_PARQUET environment variable is required.")

    # Initialize SparkSession.
    spark = SparkSession.builder.appName('LoadToFirestore').getOrCreate()
    logger.info(f"Spark session created: {spark.sparkContext.appName}")

    try:
        # Read the processed Parquet data into a Spark DataFrame.
        logger.info(f"Reading processed data from {data_processed_parquet}")
        if not os.path.exists(data_processed_parquet):
             logger.error(f"Processed Parquet file not found at: {data_processed_parquet}. Please ensure the transform task completed successfully.")
             raise FileNotFoundError(f"Processed Parquet file not found: {data_processed_parquet}")

        df = spark.read.parquet(data_processed_parquet)

        records = df.collect()
        logger.info(f"Loaded {len(records)} records into memory for upload.")

        if not firebase_admin._apps: # Check if Firebase app was initialized successfully
            logger.error("Firebase app not initialized. Cannot proceed with Firestore upload.")
            raise RuntimeError("Firebase app not initialized.")

        for row in records:
            data = row.asDict()
            # Ensure 'product_id' exists in the data
            if 'product_id' not in data:
                logger.warning(f"Skipping record due to missing 'product_id': {data}")
                continue
            doc_id = str(data['product_id'])
            db.collection('daily_sentiment').document(doc_id).set(data)
        logger.info(f"Successfully uploaded {len(records)} records to Firestore.")

    except Exception as e:
        logger.error(f"An error occurred during Firestore load: {e}", exc_info=True)
        raise # Re-raise the exception so Airflow marks the task as failed
    finally:
        # Stop the SparkSession to release resources, regardless of success or failure.
        spark.stop()
        logger.info("Spark session stopped.")

if __name__ == '__main__':
    main()