
import json

file_path = "data/raw/github_repositories.json"

with open(file_path, "r", encoding="utf-8") as file:
    repositories = json.load(file)

print("\nGITHUB REPOSITORY DETAILS\n")

for index, repo in enumerate(repositories, start=1):
    print(f"{index}. {repo['repository_name']}")
    print(f"   Description: {repo['description']}")
    print(f"   Topics: {', '.join(repo['topics'])}")
    print("-" * 60)
