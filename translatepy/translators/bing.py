from json import loads
from translatepy.models.languages import Language
from requests import post

HEADERS = {
    "Host": "www.bing.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.bing.com/",
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "keep-alive"
}
PARAMS = {'IG' : '839D27F8277F4AA3B0EDB83C255D0D70', 'IID' : 'translator.5033.3'}

class Example():
    class SourceExample():
        def __init__(self, data) -> None:
            self._data = data
            self.prefix = self._data.get("sourcePrefix", "")
            self.term = self._data.get("sourceTerm", "")
            self.suffix = self._data.get("sourceSuffix", "")
            self.example = self.prefix + self.term + self.suffix
        
        def __repr__(self) -> str:
            return str(self.example)
    class DestinationExample():
        def __init__(self, data) -> None:
            self._data = data
            self.prefix = self._data.get("targetPrefix", "")
            self.term = self._data.get("targetTerm", "")
            self.suffix = self._data.get("targetSuffix", "")
            self.example = self.prefix + self.term + self.suffix
        
        def __repr__(self) -> str:
            return str(self.example)

    def __init__(self, data) -> None:
        self._data = data
        self.source = self.SourceExample(self._data)
        self.destination = self.DestinationExample(self._data)

    def __repr__(self) -> str:
        return str(self.source)
        

class BingTranslate():
    """
    A Python implementation of Microsoft Bing Translation's APIs
    """
    def __init__(self) -> None:
        pass

    def translate(self, text, destination_language, source_language="auto-detect"):
        """
        Translates the given text to the given language
        """
        try:
            if source_language is None:
                source_language = "auto-detect"
            if isinstance(source_language, Language):
                source_language = source_language.bing_translate
            request = post("https://www.bing.com/ttranslatev3", headers=HEADERS, params=PARAMS, data={'text': str(text), 'fromLang': str(source_language), 'to': str(destination_language)})
            if request.status_code < 400:
                data = loads(request.text)
                return data[0]["detectedLanguage"]["language"], data[0]["translations"][0]["text"]
            else:
                return None, None
        except:
            return None, None


    def example(self, text, destination_language, source_language="auto-detect"):
        """
        Return examples for the given text
        """
        try:
            source_language, translation = self.translate(text, destination_language, source_language)
            if translation is None:
                return None, None
            request = post("https://www.bing.com/texamplev3", headers=HEADERS, params=PARAMS, data={'text': str(text).lower(), 'from': str(source_language), 'to': str(destination_language), 'translation': str(translation).lower()})
            if request.status_code < 400:
                return source_language, [Example(example) for example in loads(request.text)[0]["examples"]]
            else:
                return None, None
        except:
            return None, None


    def spellcheck(self, text, source_language=None):
        """
        Checks the spelling of the given text
        """
        try:
            if source_language is None:
                source_language = self.language(text)
                if source_language is None:
                    return None, None
            request = post("https://www.bing.com/tspellcheckv3", headers=HEADERS, params=PARAMS, data={'text': str(text), 'fromLang': str(source_language)})
            if request.status_code < 400:
                result = loads(request.text)["correctedText"]
                if result == "":
                    return source_language, text
                return source_language, result
            else:
                return None, None
        except:
            return None, None

    def language(self, text):
        """
        Gives back the language of the given text
        """
        try:
            request = post("https://www.bing.com/ttranslatev3", headers=HEADERS, params=PARAMS, data={'text': str(text), 'fromLang': "auto-detect", 'to': "en"})
            if request.status_code < 400:
                return loads(request.text)[0]["detectedLanguage"]["language"]
            else:
                return None
        except:
            return None

    def __repr__(self) -> str:
        return "Microsoft Bing Translator"