import os
import sys
import logging
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp
import firebase_admin
from firebase_admin import storage, credentials

# Load environment variables
load_dotenv()

# Initialize Firebase app with credentials
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
firebase_admin.initialize_app(cred)

# Setup logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger('extract_reviews')

def download_from_firebase_storage(bucket_name, source_blob_name, destination_file_name):
    """Download file from Firebase Storage"""
    bucket = storage.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    logger.info(f"Downloaded {source_blob_name} to {destination_file_name}")

if __name__ == '__main__':
    # Load environment variables
    firebase_storage_bucket = os.getenv('FIREBASE_STORAGE_BUCKET')
    data_raw_parquet = os.getenv('DATA_RAW_PARQUET')

    # Download the dataset from Firebase Storage
    source_blob_name = 'Amazon_Consumer_Reviews.csv'
    local_csv_path = '/opt/airflow/data/raw_reviews.csv'
    download_from_firebase_storage(firebase_storage_bucket, source_blob_name, local_csv_path)

    # Initialize SparkSession
    spark = SparkSession.builder \
        .appName('ExtractReviews') \
        .config('spark.sql.shuffle.partitions', '4') \
        .getOrCreate()
    logger.info(f"Spark session created: {spark.sparkContext.appName}")

    # Read raw CSV into DataFrame
    logger.info(f"Reading raw CSV from {local_csv_path}")
    df = spark.read.csv(local_csv_path, header=True, inferSchema=True)

    # Basic data validation and cleaning
    df = df.withColumnRenamed('reviews.text', 'review_text')
    df = df.dropna(subset=['review_text'])  # Drop rows with missing review text
    df = df.withColumn('ingest_ts', current_timestamp())  # Add ingestion timestamp

    # Write DataFrame to Parquet
    logger.info(f"Writing raw data to Parquet at {data_raw_parquet}")
    df.coalesce(4).write.mode('overwrite').parquet(data_raw_parquet)

    # Stop Spark session
    spark.stop()
    logger.info("Extract job completed successfully.")