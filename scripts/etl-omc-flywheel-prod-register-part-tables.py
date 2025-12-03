import sys
import boto3
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from urllib.parse import urlparse

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'DATABASE',
    'S3_ROOT',
    'TABLE_PREFIX',
    'MAX_COLS'
])

# --- CONFIGURATION FROM JOB PARAMETERS ---
DATABASE = args.get('DATABASE', 'omc_flywheel_dev')
S3_ROOT = args.get('S3_ROOT', 's3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/infobase_attributes/')
TABLE_PREFIX = args.get('TABLE_PREFIX', 'part_')
MAX_COLS = int(args.get('MAX_COLS', '100'))

print(f"📊 Job Parameters:")
print(f"  🗄️  Database: {DATABASE}")
print(f"  📁 S3 Root: {S3_ROOT}")
print(f"  🏷️  Table Prefix: {TABLE_PREFIX}")
print(f"  📊 Max Columns: {MAX_COLS}")
# ----------------------

glueContext = GlueContext(SparkContext.getOrCreate())
spark = glueContext.spark_session
glue = boto3.client("glue")

# Ensure database exists
spark.sql(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")

# List subfolders (each subfolder = one table)
parsed = urlparse(S3_ROOT)
s3 = boto3.client("s3")
resp = s3.list_objects_v2(Bucket=parsed.netloc, Prefix=parsed.path.lstrip("/"), Delimiter='/')
tables = [p['Prefix'].rstrip('/').split('/')[-1] for p in resp.get('CommonPrefixes', [])]

# Filter out metadata and other non-table folders
tables = [t for t in tables if t not in ['metadata', '.metadata', '_metadata']]

# If no subfolders found, check if there are parquet files directly in the root
if not tables:
    print("📁 No subfolders found, checking for direct parquet files...")
    resp = s3.list_objects_v2(Bucket=parsed.netloc, Prefix=parsed.path.lstrip("/"))
    parquet_files = [obj['Key'] for obj in resp.get('Contents', []) if obj['Key'].endswith('.parquet')]
    if parquet_files:
        # Extract table name from the S3_ROOT path
        table_name = S3_ROOT.rstrip('/').split('/')[-1]
        tables = [table_name]
        print(f"📋 Found direct parquet files, using table name: {table_name}")

print(f"📋 Found {len(tables)} tables: {tables}")

def spark_type_to_glue_type(dt):
    """Convert Spark type to Glue type string."""
    from pyspark.sql.types import (
        BooleanType, ByteType, ShortType, IntegerType, LongType,
        FloatType, DoubleType, StringType, DateType, TimestampType,
        BinaryType, DecimalType, ArrayType, MapType, StructType
    )
    mapping = {
        BooleanType: "boolean",
        ByteType: "tinyint",
        ShortType: "smallint",
        IntegerType: "int",
        LongType: "bigint",
        FloatType: "float",
        DoubleType: "double",
        StringType: "string",
        DateType: "date",
        TimestampType: "timestamp",
        BinaryType: "binary"
    }
    for t, name in mapping.items():
        if isinstance(dt, t):
            return name
    if isinstance(dt, DecimalType):
        return f"decimal({dt.precision},{dt.scale})"
    if isinstance(dt, ArrayType):
        return f"array<{spark_type_to_glue_type(dt.elementType)}>"
    if isinstance(dt, MapType):
        return f"map<{spark_type_to_glue_type(dt.keyType)},{spark_type_to_glue_type(dt.valueType)}>"
    if isinstance(dt, StructType):
        return "struct<" + ",".join([f"{f.name}:{spark_type_to_glue_type(f.dataType)}" for f in dt.fields]) + ">"
    return "string"

for t in tables:
    # If no subfolders were found, use the S3_ROOT directly
    if not resp.get('CommonPrefixes'):
        s3_path = f"{S3_ROOT.rstrip('/')}/"
    else:
        s3_path = f"{S3_ROOT.rstrip('/')}/{t}/"
    print(f"🧭 Registering {t} from {s3_path}")

    try:
        df = spark.read.parquet(s3_path).limit(1)
        cols = [{"Name": f.name, "Type": spark_type_to_glue_type(f.dataType)} for f in df.schema.fields[:MAX_COLS]]

        table_name = f"{TABLE_PREFIX}{t.lower()}"
        sd = {
            "Columns": cols,
            "Location": s3_path,
            "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                "Parameters": {"serialization.format": "1"}
            },
            "Compressed": True
        }
        # Read snapshot_dt from metadata file
        def get_snapshot_dt_from_metadata(s3_root):
            try:
                s3_client = boto3.client('s3')
                bucket = s3_root.split('/')[2]
                key = f"{s3_root.split('/', 3)[3]}metadata/snapshot_dt.txt"
                response = s3_client.get_object(Bucket=bucket, Key=key)
                return response['Body'].read().decode('utf-8').strip()
            except Exception as e:
                print(f"⚠️  Could not read snapshot_dt metadata: {e}")
                return None
        
        snapshot_dt = get_snapshot_dt_from_metadata(S3_ROOT)
        table_comment = f"Bucketed table created from snapshot_dt={snapshot_dt}" if snapshot_dt else "Bucketed table"
        
        table_input = {
            "Name": table_name,
            "TableType": "EXTERNAL_TABLE",
            "StorageDescriptor": sd,
            "Parameters": {
                "classification": "parquet", 
                "EXTERNAL": "TRUE",
                "comment": table_comment
            }
        }

        # Try to drop existing table first (handles Lake Formation governed tables)
        try:
            glue.delete_table(DatabaseName=DATABASE, Name=table_name)
            print(f"🗑️  Dropped existing table {DATABASE}.{table_name}")
        except glue.exceptions.EntityNotFoundException:
            pass  # Table doesn't exist, which is fine
        except Exception as drop_error:
            print(f"⚠️  Could not drop existing table (may not exist or permission issue): {drop_error}")
            # Continue anyway - will try to create/update below

        # Now create the table fresh
        try:
            glue.create_table(DatabaseName=DATABASE, TableInput=table_input)
            print(f"✅ Created table {DATABASE}.{table_name}")
        except glue.exceptions.AlreadyExistsException:
            # If table still exists, try to update it
            try:
                glue.update_table(DatabaseName=DATABASE, TableInput=table_input)
                print(f"🔄 Updated table {DATABASE}.{table_name}")
            except Exception as update_error:
                print(f"❌ Could not update table: {update_error}")
                raise

    except Exception as e:
        print(f"❌ Error registering {t}: {e}")

print("🎯 Done! All external tables are now available in Glue Catalog.")
