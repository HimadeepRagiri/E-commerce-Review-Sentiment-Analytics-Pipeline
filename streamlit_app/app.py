import os
import logging
import streamlit as st
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import firestore, credentials

# Configure logging
LOG_DIR = "/opt/airflow/logs"
LOG_FILE = os.path.join(LOG_DIR, "streamlit_app.log")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FORMAT = "%(asctime)s — %(levelname)s — %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("Starting Streamlit Sentiment Dashboard app.")

# Load environment variables
load_dotenv()
firebase_key_path = os.getenv('FIREBASE_CREDENTIALS_PATH')

try:
    # Initialize Firebase app with credentials
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase app initialized successfully.")
    else:
        logger.info("Firebase app already initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase app: {e}")
    st.error("Failed to initialize Firebase. Check logs for details.")
    st.stop()

# Initialize Firestore client
try:
    client = firestore.client()
    logger.info("Firestore client initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}")
    st.error("Failed to connect to Firestore. Check logs for details.")
    st.stop()

st.set_page_config(page_title='Sentiment Dashboard', layout='wide')
st.title('E-commerce Review Sentiment')

# Fetch daily sentiment docs
try:
    docs = client.collection('daily_sentiment').stream()
    data = [doc.to_dict() for doc in docs]
    logger.info(f"Fetched {len(data)} documents from Firestore.")
except Exception as e:
    logger.error(f"Error fetching data from Firestore: {e}")
    st.error("Error fetching data from Firestore. Check logs for details.")
    st.stop()

if not data:
    logger.warning('No data found in daily_sentiment collection.')
    st.warning('No data found. Run the Airflow DAG to populate Firestore.')
else:
    st.subheader('Average Sentiment by Product')
    st.dataframe(data)
    try:
        st.bar_chart({d['product_id']: d['avg_sentiment'] for d in data})
        logger.info("Displayed sentiment bar chart.")
    except Exception as e:
        logger.error(f"Error displaying bar chart: {e}")
        st.error("Error displaying bar chart. Check logs for details.")