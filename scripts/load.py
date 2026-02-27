import pandas as pd
from pathlib import Path
from tqdm.auto import tqdm
from sqlalchemy import create_engine

#get the path of csv files
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data"

#make the connection to the database
DATABASE_URL = "postgresql://admin:admin@localhost:5433/procurement"
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    print("Connected successfully")

'''
date_columns = [
    "date",
    "tender_datepublished",
    "tender_milestones_duedate",
    "tender_milestones_duedate_1",
    "tender_bidopening_date"
]
''' 
#getting them dynamically insted 

first_file = next(DATA_PATH.glob("*.csv"))
sample_df = pd.read_csv(first_file)
date_columns = [col for col in sample_df.columns if 'date' in col]
all_columns = set()
non_empty_columns = set()

#all non empty column 
for path in DATA_PATH.glob("*.csv"):
    df_iter = pd.read_csv(path, chunksize=1000)
    for chunk in df_iter:
        # track all columns seen
        all_columns.update(chunk.columns)

        # track columns that have at least one non-null value
        non_empty_columns.update(chunk.columns[chunk.notna().any()])

# empty columns are those with no value in amy row
empty_columns = list(all_columns - non_empty_columns)
print(f"Globally empty columns: {empty_columns}")

#kepping only the valid columns
date_columns = [col for col in date_columns if col not in empty_columns]
table_created = False

#traverse allt he files
for path in DATA_PATH.glob("*.csv"):
    #creates an iterator to load the data 
    short_name = '_'.join(path.stem.split('_')[1:])
    df_iter = pd.read_csv(path,iterator=True,chunksize=1000)
    for chunk in tqdm(df_iter,desc=short_name):
        #drops empty columns
        chunk = chunk.drop(columns=empty_columns)
        # convert date columns safely
        for col in date_columns:
            chunk[col] = pd.to_datetime(
                chunk[col],
                errors="coerce",
                format="mixed",
                dayfirst=True
            )

        #crete the table first
        if not table_created:
            chunk.head(0).to_sql(name='tender', con=engine, if_exists='replace', index=False)
            table_created = True

        #now append all the data from the csv 

        chunk.to_sql(
            name='tender',
            con=engine,
            if_exists = 'append',
            index=False
        )
    print(f"✓ Loaded {short_name}")
    
print("DONE!")
    