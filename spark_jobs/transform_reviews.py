import os
import sys
import logging
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, trim, udf, when
from pyspark.sql.types import FloatType, StringType
from textblob import TextBlob

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger('transform_reviews')

def sentiment_score(text: str) -> float:
    """
    Calculate sentiment score using TextBlob.
    Returns polarity between -1.0 (negative) and 1.0 (positive).
    """
    if text and isinstance(text, str):
        blob = TextBlob(text)
        return blob.sentiment.polarity
    return 0.0

def clean_text(text: str) -> str:
    """Additional text cleaning for robustness"""
    if text and isinstance(text, str):
        return text.strip()
    return ""

if __name__ == '__main__':
    # Load environment variables
    data_raw_parquet = os.getenv('DATA_RAW_PARQUET')
    data_processed_parquet = os.getenv('DATA_PROCESSED_PARQUET')

    # Initialize SparkSession
    spark = SparkSession.builder.appName('TransformReviews').getOrCreate()
    logger.info(f"Reading raw parquet from {data_raw_parquet}")
    df = spark.read.parquet(data_raw_parquet)

    # Rename columns for consistency
    df = df.withColumnRenamed('asins', 'product_id') \
           .withColumnRenamed('reviews.rating', 'rating')

    # Detailed text cleaning
    clean_text_udf = udf(clean_text, StringType())
    cleaned_df = df.withColumn('cleaned_text', clean_text_udf(col('review_text')))
    cleaned_df = cleaned_df.withColumn(
        'cleaned_text',
        lower(regexp_replace(col('cleaned_text'), '[^a-zA-Z0-9\s]', ''))
    )
    cleaned_df = cleaned_df.withColumn('cleaned_text', trim(col('cleaned_text')))

    # Register UDF for sentiment analysis
    sentiment_udf = udf(sentiment_score, FloatType())
    scored_df = cleaned_df.withColumn('sentiment', sentiment_udf(col('cleaned_text')))

    # Additional transformations: categorize sentiment
    categorized_df = scored_df.withColumn(
        'sentiment_category',
        when(col('sentiment') > 0.1, 'positive')
        .when(col('sentiment') < -0.1, 'negative')
        .otherwise('neutral')
    )

    # Aggregate: average sentiment and count reviews by product
    agg_df = categorized_df.groupBy('product_id') \
        .agg(
            {'sentiment': 'avg', 'rating': 'avg', 'review_text': 'count'}
        ) \
        .withColumnRenamed('avg(sentiment)', 'avg_sentiment') \
        .withColumnRenamed('avg(rating)', 'avg_rating') \
        .withColumnRenamed('count(review_text)', 'review_count')

    # Write processed data
    logger.info(f"Writing processed data to {data_processed_parquet}")
    agg_df.write.mode('overwrite').parquet(data_processed_parquet)
    spark.stop()
    logger.info("Transform job completed successfully.")