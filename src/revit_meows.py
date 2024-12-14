import time
import numpy as np
import pandas as pd
import requests
from aps_toolkit import Token
import math
import base64
import gzip
import json
from io import BytesIO
import zlib


class APSRevit:
    def __init__(self, urn: str, token: Token, region: str = "US") -> None:
        """
        Constructor for APSRevit class
        :param urn: URN of the model or item version :
        use aps_toolkit.ConvertUtils.parse_acc_url(urn) to get the URN or BIM360.get_latest_derivative_urn(project_id, item_id)
        :param token: Token object, required for authentication use 3-legged token
        use aps_toolkit.Auth().auth3leg() to get the token
        :param region: default is US, the region of the model e.g: US, EMEA
        """
        if region.lower() == "emea":
            self.host = "https://developer.api.autodesk.com/modelderivative/v2/regions/eu/designdata"
        elif region.lower() == "us":
            self.host = "https://developer.api.autodesk.com/modelderivative/v2/designdata"
        else:
            raise ValueError("Region must be US or EMEA")
        if 'version=' in urn:
            self.urn = self._item_version_to_urn(urn)
        self.urn = urn
        self.token = token

    @staticmethod
    def _urn_to_item_version(urn):
        data = urn.split("_")
        item_id = data[0]
        versionid = data[1]
        item_id = base64.b64decode(item_id + "=").decode("utf-8")
        # Manually add padding to ensure the length is a multiple of 4
        padding = "=" * (4 - len(versionid) % 4) if len(versionid) % 4 != 0 else ""
        urn_padded = versionid + padding
        versionid = base64.b64decode(urn_padded).decode("utf-8")
        item_version = item_id + "?" + versionid
        return item_version

    @staticmethod
    def _item_version_to_urn(item_version):
        data = item_version.split("?")
        item_id = data[0]
        versionid = data[1]
        item_id = base64.b64encode(item_id.encode("utf-8")).decode("utf-8")
        versionid = base64.b64encode(versionid.encode("utf-8")).decode("utf-8")
        urn = item_id + "_" + versionid
        urn = urn.replace("=", "")
        return urn

    def get_model_guid(self) -> pd.DataFrame:
        url = f"{self.host}/{self.urn}/metadata"
        headers = {'Authorization': 'Bearer ' + self.token.access_token}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            data = data['data']['metadata']
            df = pd.json_normalize(data)
            return df

    def get_master_view_model_guid(self) -> str:
        df_model_guid = self.get_model_guid()
        model_guid = df_model_guid[df_model_guid['isMasterView'] == True]['guid'].values[0]
        return model_guid

    def get_all_categories(self, model_guid=None) -> list[str]:
        """
        Get all categories of the model
        :param model_guid: default is None, if None, it will get the master view model guid
        :return:
        """
        if model_guid is None:
            model_guid = self.get_master_view_model_guid()
        url_object_tree = f'{self.host}/{self.urn}/metadata/{model_guid}?forceget=true'
        headers = {'Authorization': 'Bearer ' + self.token.access_token}
        response = requests.get(url_object_tree, headers=headers, timeout=10)
        while response.status_code != 200:
            response = requests.get(url_object_tree, headers=headers, timeout=10)
            if response.status_code != 202:
                break
            time.sleep(2)
        categories = []
        if response.status_code == 200:
            for item in response.json()["data"]["objects"]:
                for child in item.get('objects', []):
                    category = child['name']
                    categories.append(category)
        return categories

    def _recursive_category(self, child, category, cat_id, df) -> pd.DataFrame:
        if 'objects' in child:
            for item in child['objects']:
                id = str(item['objectid'])
                # Append new data to the DataFrame
                df = pd.concat([df, pd.DataFrame({"Category": [category], "CatDbId": [cat_id], "objectid": [id]})],
                               ignore_index=True)
                # Recurse into child objects
                df = self._recursive_category(item, category, cat_id, df)
        return df

    def get_object_tree_category(self, model_guid=None) -> pd.DataFrame:
        """
        Get the object tree category of the model
        :param model_guid: default is None, if None, it will get the master view model guid
        :return:
        """
        if model_guid is None:
            model_guid = self.get_master_view_model_guid()
        df_category = pd.DataFrame(columns=["Category", "objectid"])
        df_category = df_category.astype(str)
        url_object_tree = f'{self.host}/{self.urn}/metadata/{model_guid}?forceget=true'
        headers = {'Authorization': 'Bearer ' + self.token.access_token}
        response = requests.get(url_object_tree, headers=headers, timeout=10)
        while response.status_code != 200:
            response = requests.get(url_object_tree, headers=headers, timeout=10)
            if response.status_code != 202:
                break
            time.sleep(2)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"Failed to get object tree: {response.text}", response.status_code)
        for item in response.json()["data"]["objects"]:
            for child in item.get('objects', []):
                category = child['name']
                cat_id = str(child['objectid'])
                df_category = self._recursive_category(child, category, cat_id, df_category)
        # cast object_id to int64
        df_category['objectid'] = df_category['objectid'].astype(np.int64)
        # Reset index of the final DataFrame
        df_category = df_category.reset_index(drop=True)
        return df_category

    def get_all_data(self, model_guid=None, is_field_param=False, is_include_category=False) -> pd.DataFrame:
        """
        Get all data of the model with the option to include the category
        :param model_guid: the model guid, default is None, if None, it will get the master view model guid
        :param is_field_param: default is False, if True, it will include the field param in the column name e.g: [Dimension]Width if True and Width if False
        :param is_include_category: default is False, if True, it will include the column Category
        :return: pandas DataFrame
        """
        if model_guid is None:
            model_guid = self.get_master_view_model_guid()
        url = f"{self.host}/{self.urn}/metadata/{model_guid}/properties?forceget=true"
        headers = {'Authorization': f'Bearer {self.token.access_token}',
                   "Accept-Encoding": "gzip, deflate",
                   "Content-Type": "application/json",
                   "x-ads-force": "true"
                   }
        response = requests.get(url, headers=headers, timeout=10)
        while response.status_code != 200:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 202:
                break
            time.sleep(2)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"Failed to get all data: {response.text}", response.status_code)
        data = response.json()
        rows = []
        if "data" not in data:
            return pd.DataFrame()
        if "collection" not in data["data"]:
            return pd.DataFrame()
        for item in data["data"]["collection"]:
            row = {
                "objectid": item["objectid"],
                "name": item["name"],
                "externalId": item["externalId"],
            }
            # Flatten the properties dictionary
            properties = item.get("properties", {})
            for key, value in properties.items():
                if isinstance(value, dict):  # Flatten nested dictionaries
                    for sub_key, sub_value in value.items():
                        if is_field_param:
                            row[f"[{key}]{sub_key}"] = sub_value
                        else:
                            row[sub_key] = sub_value
                else:
                    row[key] = value
            rows.append(row)
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        df = df[df['name'].str.contains(r'\[\d+\]', na=False)]
        df['ElementId'] = df['name'].str.extract(r'\[(\d+)\]', expand=False)
        df['Family Name'] = df['name'].str.replace(r'\[\d+\]', '', regex=True)
        df = df[['objectid', 'name', 'ElementId', "externalId", "Family Name"] + \
                [col for col in df.columns if
                 col not in ['objectid', 'name', 'ElementId', 'externalId', 'Family Name']]]
        df = df.reset_index(drop=True)
        if is_include_category:
            df_category = self.get_object_tree_category(model_guid)
            if df_category.empty:
                return df
            df_category = df_category.drop(columns=['CatDbId'])
            total_df = df.merge(df_category, on='objectid', how='left')
            total_df = total_df[['objectid', 'name', 'ElementId', "externalId", "Family Name", "Category"] +
                                [col for col in total_df.columns if
                                 col not in ['objectid', 'name', 'ElementId', 'externalId', 'Family Name', "Category"]]]
            return total_df
        return df

    def get_data_by_object_ids(self, model_guid=None, object_ids: list[int] = None,
                               is_field_param=False) -> pd.DataFrame:
        """
        Get data by object ids
        :param model_guid:  default is None, if None, it will get the master view model guid
        :param object_ids:  list of object ids
        :param is_field_param:  default is False, if True, it will include the field param in the column name e.g: [Dimension]Width if True and Width if False
        :return:
        """
        if model_guid is None:
            model_guid = self.get_master_view_model_guid()
        if object_ids is None:
            object_ids = [1]
        url = f"{self.host}/{self.urn}/metadata/{model_guid}/properties:query"
        limit = 999
        offset = 0
        headers = {'Authorization': f'Bearer {self.token.access_token}',
                   "Accept-Encoding": "gzip, deflate",
                   "Content-Type": "application/json",
                   "x-ads-force": "true"
                   }
        if len(object_ids) > 1000:
            raise ValueError("Object ids must be less than 1000, please split the object ids to less than 1000")
        payload = {
            "query": {
                "$in": ["objectid"] + [int(i) for i in object_ids]
            },
            "fields": [
                "objectid",
                "name",
                "externalId",
                "properties"
            ],
            "pagination": {
                "offset": offset,
                "limit": limit
            },
            "payload": "text"
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        while response.status_code != 200:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 202:
                break
            time.sleep(2)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"Failed to get data by object ids: {response.text}",
                                                response.status_code)
        data = response.json()
        df = self._convert_to_data_frame(data)
        if df.empty:
            return pd.DataFrame()
        total_count = data["pagination"]["totalResults"]
        if total_count > limit:
            # count loop offset with limit number set
            loop = math.ceil(total_count / limit)
            for i in range(1, loop):
                offset = i * limit
                payload["pagination"]["offset"] = offset
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                while response.status_code != 200:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code != 202:
                        break
                    time.sleep(2)
                data = response.json()
                df = pd.concat([df, self._convert_to_data_frame(data, is_field_param)], ignore_index=True)
        df = self._apply_more_column(df)
        return df

    def _convert_to_data_frame(self, payload, is_field_param=False) -> pd.DataFrame:
        rows = []
        if "data" not in payload:
            return pd.DataFrame()
        if "collection" not in payload["data"]:
            return pd.DataFrame()
        for item in payload["data"]["collection"]:
            row = {
                "objectid": item["objectid"],
                "name": item["name"],
                "externalId": item["externalId"],
            }
            # Flatten the properties dictionary
            properties = item.get("properties", {})
            for key, value in properties.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if is_field_param:
                            row[f"[{key}]{sub_key}"] = sub_value
                        else:
                            row[sub_key] = sub_value
            rows.append(row)
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        return df

    def _apply_more_column(self, df):
        df = df[df['name'].str.contains(r'\[\d+\]', na=False)]
        df['ElementId'] = df['name'].str.extract(r'\[(\d+)\]', expand=False)
        df['Family Name'] = df['name'].str.replace(r'\[\d+\]', '', regex=True)
        df = df[['objectid', 'name', 'ElementId', "externalId", "Family Name"] + \
                [col for col in df.columns if
                 col not in ['objectid', 'name', 'ElementId', 'externalId', 'Family Name']]]
        return df

    def get_data_by_categories(self, categories: list[str], model_guid=None, is_field_param=False) -> pd.DataFrame:
        """
        Get all data by revit categories list , e.g: ["Walls", "Doors"]
        :param categories: list of categories
        :param model_guid: the model guid, default is None, if None, it will get the master view model guid
        :return: pandas DataFrame
        """
        df_tree = self.get_object_tree_category(model_guid)
        df_tree_filter = df_tree[df_tree['Category'].isin(categories)]
        if df_tree_filter.empty:
            return pd.DataFrame()
        object_ids = df_tree_filter['objectid'].tolist()
        if not object_ids or len(object_ids) == 0:
            return pd.DataFrame()

        if len(object_ids) > 1000:
            # chuck to list in list
            object_ids_arrays = [object_ids[i:i + 1000] for i in range(0, len(object_ids), 1000)]
        else:
            object_ids_arrays = [object_ids]
        df = pd.DataFrame()
        for object_ids in object_ids_arrays:
            df_single = self.get_data_by_object_ids(model_guid, object_ids=object_ids, is_field_param=is_field_param)
            df = pd.concat([df, df_single], ignore_index=True)
        # drop column CatDbId
        df_tree = df_tree.drop(columns=['CatDbId'])
        # merge to add new category column
        df = df.merge(df_tree, on='objectid', how='left')
        df = df[['objectid', 'name', 'ElementId', "externalId", "Family Name", "Category"] + \
                [col for col in df.columns if
                 col not in ['objectid', 'name', 'ElementId', 'externalId', 'Family Name', "Category"]]]
        return df

    def get_bounding_boxs(self, project_id) -> pd.DataFrame:
        item_version = self._urn_to_item_version(self.urn)
        url = f"https://developer.api.autodesk.com/construction/index/v2/projects/{project_id}/indexes:batch-status"
        headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "versions": [{
                "versionUrn": item_version
            }]
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"Failed to get bounding box: {response.text}", response.status_code)
        version_index_result = response.json()
        while version_index_result["indexes"][0]["state"] != "FINISHED":
            response = requests.post(url, headers=headers, json=data)
            version_index_result = response.json()
            time.sleep(2)
        propertiesUrl = response.json()["indexes"][0]["propertiesUrl"]
        headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip"
        }
        property_result = requests.get(propertiesUrl, headers=headers)
        if property_result.status_code != 200:
            raise requests.exceptions.HTTPError(f"Failed to get bounding box: {property_result.reason}",
                                                property_result.status_code)
        bytes_io = BytesIO()
        encoding = property_result.headers.get("Content-Encoding")
        if encoding == "gzip":
            with gzip.GzipFile(fileobj=bytes_io, mode="wb") as f:
                f.write(property_result.content)
        elif encoding == "deflate":
            decompressed_data = zlib.decompress(property_result.content)
            bytes_io.write(decompressed_data)
        data = gzip.decompress(bytes_io.getvalue())
        data = data.decode("utf-8")
        data = "[" + data.replace("\n", ",")[:-1] + "]"
        json_object = json.loads(data)
        single_df = pd.json_normalize(json_object, max_level=1)
        df_bbox = single_df[
            ["otgId", "externalId", "bboxMin.x", "bboxMin.y", "bboxMin.z", "bboxMax.x", "bboxMax.y", "bboxMax.z"]]
        df_bbox = df_bbox.rename(columns={"otgId": "object_id"})
        return df_bbox

    def get_all_data_bbox(self, project_id, model_guid=None, is_field_param=False,
                          is_include_category=False) -> pd.DataFrame:
        """
        Get all data with bounding box information included, bbox information is in the columns bboxMin.x, bboxMin.y, bboxMin.z, bboxMax.x, bboxMax.y, bboxMax.z
        Unit is in feet
        :param project_id:
        :param model_guid:
        :param is_field_param:
        :param is_include_category:
        :return:
        """
        df = self.get_all_data(model_guid, is_field_param, is_include_category)
        df_bbox = self.get_bounding_boxs(project_id)
        df_bbox = df_bbox.drop(columns=['object_id'])
        df_merge = pd.merge(df, df_bbox, on="externalId")
        return df_merge
