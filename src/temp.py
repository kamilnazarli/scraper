record = 10
invalid_records = []
invalid_records.append({"record": {record}})
print(invalid_records)

try:
    a = "a" + 5
except Exception as e:
    print(str(e))
    print(type(e))