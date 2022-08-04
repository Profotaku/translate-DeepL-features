# `translatepy` (originally: translate)

### A fork of [translatepy](https://github.com/Animenosekai/translate) with DeepL tonality and glossary support.

## Notes

This fork exists until these features are integrated properly into version 3.0: in translatepy. After that, it will no longer be maintained.

## Installing

### From Git:

```bash
pip install --upgrade git+https://github.com/Profotaku/translate-DeepL-features
```

You can check if you successfully installed it by printing out its version:

```bash
$ translatepy --version
# output:
translatepy v2.4 (Deepl)
```

or just:

```bash
$ python -c "import translatepy; print(translatepy.__version__)"
# output:
translatepy v2.4 (Deepl)
```

## How to use

```python
from translatepy.translators.deepl import DeeplTranslate
translator = DeeplTranslate()
glossary = translator.load_glossary_from_csv(file_path='dictionary.csv', separator=';', encoding='utf-8', source_language='en', target_language='fr')
translation = translator.translate(text="""text to translate""", destination_language="fr", source_language="en", formality='informal', glossary=glossary)
print(translation)
```

#### Formality

The argument is optional. It can be one of the following:

- informal: Corresponds to "less" in official API.
- formal: Corresponds to "more" in official API.
- None: Coresponds to the "auto" mode, default value.

#### Glossary

- The argument is optional.
- Your CSV file should follow the following format:

| Source Language (ISO 639-1) | Target Language (ISO 639-1) |
|-----------------------------|-----------------------------|
| Source Text 1               | Target Text 1               |
| Source Text 2               | Target Text 2               |

#####  Exemple
| EN               | FR                  |
|------------------|---------------------|
| Hello !          | Bonjour !           |
| A beautiful text | Un magnifique texte |
- Currently glossaries for the following language combinations are supported (see DeepL's documentation for more informations):

    - EN <=> FR, DE, ES, IT, PL, JA
    - FR <=> EN, DE
    - DE <=> EN, FR
    - ES <=> EN
    - IT <=> EN
    - PL <=> EN
    - JA <=> EN

- As on the website, you can load 10 combinations per request but the module function automatically selects the combinations present in the text to be translated.
- So you **can** load a csv with **more than** 10 entries but if your text to be translated contains more than 10 terms that are in your glossary, you will see a warning telling you that only the first 10 combinations will be used in the query.
- CSV with UTF-8 encoding is strongly recommended.
- Double-quotes are automatically deleted (Please don't use them in your CSV file).

## Issues/Pull requests

If your problem/pull request is about the implemented DeepL features, you can open an issue, if your problem is about something else, please open an issue [here](https://github.com/Animenosekai/translate/issues).

## Built With

- [pyuseragents](https://github.com/Animenosekai/useragents) - To generate the "User-Agent" HTTP header
- [requests](https://github.com/psf/requests) - To make HTTP requests
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) - To parse HTML
- [inquirer](https://github.com/magmax/python-inquirer) - To make beautiful CLIs
- [pandas](https://github.com/pandas-dev/pandas) - To parse CSV files

## Authors

- **Anime no Sekai** - *Initial work* - [Animenosekai](https://github.com/Animenosekai)
- **Zhymabek Roman** - *Major Contributor (PR #10, PR #15)* - [ZhymabekRoman](https://github.com/ZhymabekRoman)
- **Profotaku** - *Initiator of this fork* - [Profotaku](https://github.com/Profotaku)

## Disclaimer

Please **do not** use this module in a commercial manner. Pay a proper API Key from one of the services to do so.

## License

This project is licensed under the GNU Affero General Public License v3.0 License - see the [LICENSE](LICENSE) file for details