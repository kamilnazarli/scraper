import requests

r = requests.get("https://books.toscrape.com/robots.txt")

print(r)