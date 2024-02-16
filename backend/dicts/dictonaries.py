import os
import json
from uuid import UUID
from typing import Dict, Union
from backend.config.const import REPLACEMENTS


class Dicts(object):

    def __init__(self, folder_path: str = '.') -> None:
        """
        replace_dict: a dictionary to replace chars in source text
        dictionaries: a dictionary of dictionaries to correct language dependent translation mistakes
        """
        module_path = os.path.join(os.path.dirname(os.path.relpath(__file__)), folder_path)
        self.folder_path = os.path.join(module_path, 'json')
        self.replacements: Dict[str, str] = REPLACEMENTS
        self.dictionaries: Dict[str, Dict[str, str]] = {}

    def load(self, uuid: Union[UUID, str]) -> None:
        """
        :param uuid: user uuid to identify correspondent dictionaries
        """
        json_path = os.path.join(self.folder_path, f'{uuid}.json')
        if os.path.isfile(json_path):
            with open(file = json_path, mode = 'r', encoding = 'utf-8') as json_file:
                data = json.load(json_file)
            self.replacements = data.get('replacements', {})
            self.dictionaries = data.get('dictionaries', {})
        else:
            self.save(uuid = uuid)

    def save(self, uuid: Union[UUID, str]) -> None:
        """
        :param uuid: user uuid to identify correspondent dictionaries
        """
        os.makedirs(self.folder_path, exist_ok = True)
        json_path = os.path.join(self.folder_path, f'{uuid}.json')
        with open(file = json_path, mode = 'w', encoding = 'utf-8') as json_file:
            data = {'replacements': self.replacements, 'dictionaries': self.dictionaries}
            json.dump(data, json_file, ensure_ascii = False, indent = 4)
