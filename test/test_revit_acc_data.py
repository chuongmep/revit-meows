from unittest import TestCase
from aps_toolkit import Auth
from .context import APSRevit
import os
import json

class TestRevitACCData(TestCase):
    def setUp(self):
        self.urn = "dXJuOmFkc2sud2lwcHJvZDpmcy5maWxlOnZmLk9kOHR4RGJLU1NlbFRvVmcxb2MxVkE_dmVyc2lvbj0zNg"
        # self.urn = "dXJuOmFkc2sud2lwcHJvZDpmcy5maWxlOnZmLk5nLWVQNzA3UW9xQlpNQ2pud180QWc_dmVyc2lvbj00"
        self.project_id = "ec0f8261-aeca-4ab9-a1a5-5845f952b17d"
        # read refresh token from config.json file
        file_name = "config.json"
        if not os.path.exists(file_name):
            os.mknod(file_name)
        with open(file_name) as json_file:
            data = json.load(json_file)
            self.refresh_token = data['refresh_token']
        self.token = Auth.refresh_token_from_env(self.refresh_token)
        # save to json refresh token
        with open(file_name, 'w') as json_file:
            data['refresh_token'] = self.token.refresh_token
            json.dump(data,json_file,indent=2)
        self.aps_revit = APSRevit(self.urn, self.token)
    def test_get_model_guid(self):
        df_model_guid = self.aps_revit.get_model_guid()
        self.assertIsNotNone(df_model_guid)
        self.assertNotEqual(len(df_model_guid), 0)

    def test_get_master_view_model_guid(self):
        df_master_view_model_guid = self.aps_revit.get_master_view_model_guid()
        self.assertIsNotNone(df_master_view_model_guid)
        self.assertNotEqual(len(df_master_view_model_guid), 0)

    def test_get_all_categories(self):
        categories = self.aps_revit.get_all_categories()
        self.assertIsNotNone(categories)
        self.assertNotEqual(len(categories), 0)
        print(categories)

    def test_get_object_tree_category(self):
        df_object_tree_category = self.aps_revit.get_object_tree_category()
        self.assertIsNotNone(df_object_tree_category)
        self.assertNotEqual(len(df_object_tree_category), 0)

    def test_get_all_data(self):
        data = self.aps_revit.get_all_data(is_field_param=True, is_include_category=True)
        self.assertIsNotNone(data)
        self.assertNotEqual(len(data), 0)
        print(data)

    def test_get_data_by_object_ids(self):
        data = self.aps_revit.get_data_by_object_ids(object_ids=[1542, 1543])
        self.assertIsNotNone(data)
        self.assertNotEqual(len(data), 0)
        print(data)

    def test_get_data_by_category(self):
        data = self.aps_revit.get_data_by_categories(["Mechanical Equipment","Rooms"])
        self.assertIsNotNone(data)
        self.assertNotEqual(len(data), 0)
        print(data)

    def test_get_bounding_boxs(self):
        data = self.aps_revit.get_bounding_boxs(self.project_id)
        self.assertIsNotNone(data)
        self.assertNotEqual(len(data), 0)
        print(data)

    def test_get_all_data_bbox(self):
        data = self.aps_revit.get_all_data_bbox(self.project_id,is_field_param=True,is_include_category=True)
        self.assertIsNotNone(data)
        self.assertNotEqual(len(data), 0)
        print(data)
