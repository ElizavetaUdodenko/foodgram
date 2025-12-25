import json


def main(file_path):
    with open(file_path, 'r') as file:
        res = json.load(file)

    i = 1
    output = []
    for item in res:
        output.append({'model': 'social.ingredient', 'pk': i, 'fields': item})
        i += 1

    with open('/Users/Elizaveta/Documents/Dev/foodgram/backend/foodgram/data/new.json', 'w', encoding='utf-8') as file:
        json.dump(output, file, ensure_ascii=False)


if __name__ == '__main__':
    main('/Users/Elizaveta/Documents/Dev/foodgram/backend/foodgram/data/ingredients.json')
