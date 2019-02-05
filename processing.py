import csv

def exists(name: str):
    with open('results.csv') as csvfile:

        reader = csv.DictReader(csvfile)

        for row in reader:
            # print(row["hotel"])
            if name == row["hotel"]:
                return True
        return False
