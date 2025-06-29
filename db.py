from pymongo import MongoClient

client = MongoClient("mongodb+srv://Sharav:saravanan123@cluster0.a1h5cs9.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["textiles_db"]

users = db["users"]
products = db["products"]
cart = db["cart"]
orders = db['orders']
wishlist = db['wishlist']
reviews = db['reviews']
feedbacks = db['feedbacks'] 