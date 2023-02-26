"""
DeepL

About the translation and the language endpoints:
    This implementation of DeepL follows Marocco2's implementation of DeepL's JSONRPC API\n
    Arrangements and optimizations have been made\n
    Refer to Issue Animenosekai/translate#7 on GitHub for further details

© Anime no Sekai — 2022
"""

from time import time, sleep
from re import compile
from random import randint
from bs4 import BeautifulSoup
import pandas as pd
import warnings
from translatepy.language import Language
from translatepy.translators.base import BaseTranslator, BaseTranslateException
from translatepy.utils.annotations import Tuple, List
from translatepy.utils.request import Request


SENTENCES_SPLITTING_REGEX = compile('(?<=[.!:?]) +')


class DeeplTranslateException(BaseTranslateException):
    """
    Default DeepL Translate exception
    """

    error_codes = {
        -32600: 'Invalid Request: Invalid commonJobParams.',
        1042911: "Too many requests.",
        1042912: "Too many requests.",
        1156049: "Invalid Request",
        5000: "Unsported language for glossary.",  # arbitrary error numbers
        5001: "Invalid CSV file: Same source and target language.",
        5002: "Invalid CSV file: EN can only be combined with FR, DE, ES, IT, PL, JA, NL.",
        5003: "Invalid CSV file: FR can only be combined with EN, DE, ES, IT, PL, JA, NL.",
        5004: "Invalid CSV file: DE can only be combined with EN, FR, ES, IT, PL, JA, NL.",
        5005: "Invalid CSV file: ES can only be combined with EN, FR, DE, IT, PL, JA, NL.",
        5006: "Invalid CSV file: IT can only be combined with EN, FR, DE, ES, PL, JA, NL.",
        5007: "Invalid CSV file: PL can only be combined with EN, FR, DE, ES, IT, JA, NL.",
        5008: "Invalid CSV file: JA can only be combined with EN, FR, DE, ES, IT, PL, NL.",
        5009: "Invalid CSV file: NL can only be combined with EN, FR, DE, ES, IT, PL, JA.",
        5010: "Invalid CSV file: Error in the header (or in its declaration in the 'load_glossary_from_csv' function)",
        5011: "Syntax Error: The combination in the glossary does not correspond to the combination declared in the translate function.",
    }


class GetClientState:
    """
    DeepL Translate state manager
    """

    def __init__(self, request: Request):
        self.id_number = randint(1000, 9999) * 10000
        self.session = request

    def dump(self) -> dict:
        self.id_number += 1
        return {
            'id': self.id_number,
            'jsonrpc': '2.0',
            'method': 'getClientState',
            'params': {
                'v': '20180814',
                'clientVars': {},
            },
        }

    def get(self) -> int:
        """
        Returns a new Client State ID
        """
        request = self.session.post("https://w.deepl.com/web", params={'request_type': 'jsonrpc', 'il': 'E', 'method': 'getClientState'}, json=self.dump())
        response = request.json()
        return response["id"]


class JSONRPCRequest:
    """
    JSON RPC Request Sender for DeepL
    """

    def __init__(self, request: Request) -> None:
        self.client_state = GetClientState(request)
        try:
            self.id_number = self.client_state.get()
        except Exception:
            self.id_number = (randint(1000, 9999) * 10000) + 1  # ? I didn't verify the range, but it's better having only DeepL not working than having Translator() crash for only one service
        self.session = request
        self.last_access = 0

    def dump(self, method, params):
        self.id_number += 1
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.id_number,
        }

    def send_jsonrpc(self, method, params):
        # Take a break 5 sec between requests, so as not to get a block by the IP address
        if time() - self.last_access < 5:
            distance = 5 - (time() - self.last_access)
            sleep(max(distance, 0))

        request = self.session.post("https://www2.deepl.com/jsonrpc", json=self.dump(method, params))
        self.last_access = time()
        response = request.json()
        if request.status_code == 200:
            return response["result"]
        else:
            raise DeeplTranslateException(response["error"]["code"])


class DeeplTranslate(BaseTranslator):
    _supported_languages = {'AUTO', 'BG', 'ZH', 'CS', 'DA', 'NL', 'NL', 'EN', 'ET', 'FI', 'FR', 'DE', 'EL', 'HU', 'IT', 'JA', 'LV', 'LT', 'PL', 'PT', 'RO', 'RO', 'RO', 'RU', 'SK', 'SL', 'ES', 'ES', 'SV'}
    _glossary_supported_languages = {'DE', 'EN', 'ES', 'FR', 'JA', 'IT', 'PL', 'NL'}

    def __init__(self, request: Request = Request(), preferred_langs: List = ["EN", "FR"]) -> None:
        self.session = request
        self.jsonrpc = JSONRPCRequest(request)
        self.user_preferred_langs = preferred_langs

    def _split_into_sentences(self, text: str, destination_language: str, source_language: str) -> Tuple[List[str], str]:
        """
        Split a string into sentences using the DeepL API.\n
        Fallbacks to a simple Regex splitting if an error occurs or no result is found

        Returned tuple: (Result, Computed Language (None if same as source_language))
        """
        REGEX_SPLIT = True

        if REGEX_SPLIT:
            SENTENCES_SPLITTING_REGEX.split(text), None

        params = {
            "texts": [text.strip()],  # What for need strip there?
            "lang": {
                "lang_user_selected": source_language,
                "user_preferred_langs": list(set(self.user_preferred_langs + [destination_language]))
            }
        }
        resp = self.jsonrpc.send_jsonrpc("LMT_split_into_sentences", params)

        return resp["splitted_texts"][0], resp["lang"]

    def load_glossary_from_csv(self, file_path: str, separator: str = ";", encoding: str = "utf-8",
                               source_language: str = "EN",
                               target_language: str = "FR") -> BaseTranslator.FormatedGlossary:
        """
        Load a glossary from a CSV file.
        The CSV file must have :
            - Source Text column
            - Target Text column
            - Header row with the languages (ISO 639-1)
        If you use the glossary with Polish or Japanese:
        Make sure you have an encoding compatible with these languages (UTF-8 is strongly recommended)
        """

        source_language = source_language.upper()
        target_language = target_language.upper()
        # verifiy if language is supported
        if source_language not in self._glossary_supported_languages or target_language not in self._glossary_supported_languages:
            raise DeeplTranslateException(5000)
        if source_language == target_language:
            raise DeeplTranslateException(5001)
        csv = pd.read_csv(file_path, sep=separator, encoding=encoding)
        # check if combinations of source and target language are available by DeepL
        if source_language == "EN" and target_language not in ["FR", "DE", "ES", "IT", "PL", "JA", "NL"]:
            raise DeeplTranslateException(5002)
        if source_language == "FR" and target_language not in ["EN", "DE", "ES", "IT", "PL", "JA", "NL"]:
            raise DeeplTranslateException(5003)
        if source_language == "DE" and target_language not in ["EN", "FR", "ES", "IT", "PL", "JA", "NL"]:
            raise DeeplTranslateException(5004)
        if source_language == "ES" and target_language not in ["EN", "FR", "DE", "IT", "PL", "JA", "NL"]:
            raise DeeplTranslateException(5005)
        if source_language == "IT" and target_language not in ["EN", "FR", "DE", "ES", "PL", "JA", "NL"]:
            raise DeeplTranslateException(5006)
        if source_language == "PL" and target_language not in ["EN", "FR", "DE", "ES", "IT", "JA", "NL"]:
            raise DeeplTranslateException(5007)
        if source_language == "JA" and target_language not in ["EN", "FR", "DE", "ES", "IT", "PL", "NL"]:
            raise DeeplTranslateException(5008)
        if source_language == "NL" and target_language not in ["EN", "FR", "DE", "ES", "IT", "PL", "JA"]:
            raise DeeplTranslateException(5009)
        csv.columns = csv.columns.str.upper()
        try:
            csv.sort_values(by=[source_language], axis=0, ascending=True, inplace=True, na_position='first')
            if not csv[source_language].is_unique:
                warnings.warn(
                    'Duplicate entries in the dictionary, only the last one will be kept. Please check the dictionary.')
                csv.drop_duplicates(subset=[source_language], keep='last', inplace=True)
        except KeyError:
            raise DeeplTranslateException(5010)
        return BaseTranslator.FormatedGlossary(csv, source_language, target_language)

    def _translate(self, text: str, destination_language: str, source_language: str, formality: str = None,
                   dictionary: BaseTranslator.FormatedGlossary = None) -> str:
        # check if glossary conbination are same as source and target language
        formated_string = ""
        priority = 1
        quality = ""
        if dictionary != "":
            if source_language.upper() not in dictionary.source_language or destination_language.upper() not in dictionary.target_language:
                raise DeeplTranslateException(5011)
            limit = 10
            # check if word in the first column in disctionnary is in the text to translate
            for word in dictionary.dataframe[source_language.upper()]:
                if word in text and limit > 0:
                    index = dictionary.dataframe[source_language.upper()].loc[lambda x: x == word].index
                    target_word = dictionary.dataframe[dictionary.target_language.upper()][index]
                    if '"' not in target_word.values[0] and '"' not in word:
                        limit -= 1
                        formated_string += word + "\t" + target_word.values[0] + "\n"
                    else:
                        # warning for words with quotes
                        warnings.warn('Word with quotes in the dictionary: the pair will be ignored')
                if word in text and limit == 0:
                    warnings.warn(
                        'The limit of 10 combinations per query has been reached, the rest of the combinations will be ignored')
            if formated_string != "":
                formated_string = formated_string.replace('"\t"\n', '')
                if formated_string[-1] == '\n':
                    formated_string = formated_string[:-1]

        # splitting the text into sentences
        sentences, computed_lang = self._split_into_sentences(text, destination_language, source_language)

        # building the a job per sentence
        jobs = self._build_jobs(sentences, quality)

        i_count = 1 + sum(sentence.count("i") for sentence in sentences)
        ts = int(time() * 10) * 100 + 1000
        # params building
        params = {
            "jobs": jobs,
            "lang": {
                "preference": {
                    "weight": {},
                    "default": "default"
                },
                "source_lang_computed": source_language,
                "target_lang": destination_language,
            },
            "priority": priority,
            "commonJobParams": {
                "browserType": 1,
                "formality": formality,
                "mode": "translate",
                "termbase": {"dictionary": formated_string}
            },
            "timestamp": ts + (i_count - ts % i_count)
        }

        if source_language == "auto":
            params["lang"]["source_lang_computed"] = computed_lang
            params["lang"]["user_preferred_langs"].append(computed_lang)
        else:
            params["lang"]["source_lang_user_selected"] = source_language

        results = self.jsonrpc.send_jsonrpc("LMT_handle_jobs", params)

        try:
            _detected_language = results["source_lang"]
        except:
            _detected_language = source_language

        if results is not None:
            translations = results["translations"]
            return _detected_language, " ".join(obj["beams"][0]["sentences"][0]["text"] for obj in translations if obj["beams"][0]["sentences"][0]["text"])

    def _language(self, text: str) -> str:
        priority = 1
        quality = ""

        # splitting the text into sentences
        sentences, computed_lang = self._split_into_sentences(text, "EN", "AUTO")

        # building the a job per sentence
        jobs = self._build_jobs(sentences, quality)

        i_count = 1 + sum(sentence.count("i") for sentence in sentences)
        ts = int(time() * 10) * 100 + 1000

        # params building
        params = {
            "jobs": jobs,
            "lang": {
                "preference": {"weight": {}, "default": "default"},
                "target_lang": "FR",
                "user_preferred_langs": ["FR"]
            },
            "priority": priority,
            "timestamp": ts + (i_count - ts % i_count)
        }

        if computed_lang is not None:
            params["lang"]["source_lang_computed"] = computed_lang
            params["lang"]["user_preferred_langs"].append(computed_lang)
        else:
            params["lang"]["source_lang_user_selected"] = "AUTO"

        results = self.jsonrpc.send_jsonrpc("LMT_handle_jobs", params)

        if results is not None:
            return results["source_lang"]

    def _dictionary(self, text: str, destination_language: str, source_language: str) -> str:
        if source_language == "AUTO":
            source_language = self._language(text)

        destination_language = Language(destination_language).name.lower()
        source_language = Language(source_language).name.lower()

        request = self.session.post("https://dict.deepl.com/" + source_language + "-" + destination_language + "/search?ajax=1&source=" + source_language + "&onlyDictEntries=1&translator=dnsof7h3k2lgh3gda&delay=800&jsStatus=0&kind=full&eventkind=keyup&forleftside=true", data={"query": text})
        if request.status_code < 400:
            response = BeautifulSoup(request.text, "html.parser")
            _result = [
                element.text.replace("\n", "")
                for element in response.find_all("a")
                if element.has_attr('class') and "dictLink" in element["class"]
            ]
            return source_language, _result

    def _build_jobs(self, sentences, quality=""):
        """
        Builds a job for each sentence for DeepL
        """
        jobs = []
        for index, sentence in enumerate(sentences):
            if index == 0:
                try:
                    before = []
                    after = [sentences[index + 1]]
                except IndexError:  # index == len(sentences) - 1
                    before = []
                    after = []
            else:
                if len(before) > 4:
                    before.pop(0)  # the "before" array cannot be more than 5 elements long i guess?
                before.extend([sentences[index - 1]])
                after = [] if index > len(sentences) - 2 else [sentences[index + 1]]
            job = {
                "kind": "default",
                "preferred_num_beams": 4,
                "raw_en_context_after": after.copy(),
                "raw_en_context_before": before.copy(),
                "sentences": [{"text": sentence, "id": 0, "prefix": ""}],

            }
            if quality != "":
                job["quality"] = quality
            jobs.append(job)

        return jobs

    def _language_normalize(self, language):
        return "ZH" if language.id == "zho" else language.alpha2.upper()

    def _language_denormalize(self, language_code):
        if str(language_code).lower() in {"zh", "zh-cn"}:
            return Language("zho")
        return Language(language_code)

    def __str__(self) -> str:
        return "DeepL"
