# from src.data.load_data import load_data
 
# df = load_data("data/raw/Reviews.csv")
 
# print(df.head())
# print(df.columns)

# from src.data.load_data import load_data
# from src.data.preprocess import create_sentiment
 
# df = load_data("data/raw/Reviews.csv")
 
# df["sentiment"] = df["Text"].apply(
#     create_sentiment
# )
 
# print(
#     df[["Text","sentiment"]].head()
# )

# from src.data.preprocess import clean_text
 
# sample = """
# This product is AMAZING!!!
# I bought 2 units.
# """
 
# print(clean_text(sample))

from src.data.process_dataset import process_dataset
 
process_dataset()


