#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import pendulum
import requests
from requests.auth import AuthBase
from airbyte_cdk.models import SyncMode 
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream, HttpSubStream
from airbyte_cdk.sources.streams.http.requests_native_auth.abstract_token import AbstractHeaderAuthenticator 

"""
TODO: There are additional required TODOs in the files within the integration_tests folder.
"""


class Cin7CoreStream(HttpStream, ABC):
    url_base = "https://inventory.dearsystems.com/ExternalApi/v2/"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None
    
    def backoff_time(self, response: requests.Response) -> Optional[float]:
        """
        Back off for 61 seconds which is above the current timeout of 60 seconds for the API
        """
        return 61

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        yield {}


# Basic incremental stream
class IncrementalCin7CoreStream(Cin7CoreStream, ABC):
    @property
    def cursor_field(self) -> str:
        return True

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        current = current_stream_state.get(self.cursor_field, "")
        latest = latest_record.get(self.cursor_field, "")

        return {
            self.cursor_field: max(current, latest)
        }


class Customers(Cin7CoreStream):
    primary_key = "ID"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "customer"

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = { "limit": 1000, "IncludeDeprecated": "true" }

        if next_page_token:
            params.update(next_page_token)

        return params

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        if response.json():
            total_records = response.json()["Total"]
            current_page = response.json()["Page"]

            if current_page < total_records / 1000:
                return {"page": current_page + 1}

        return None

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        return response.json()["CustomerList"]


class Sales(IncrementalCin7CoreStream):
    cursor_field = "Updated"
    primary_key = "SaleID"
    deduplication_buffer_minutes = 1

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.sales_created_since = config["sales_created_since"]

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "saleList"

    def stream_slices(self, stream_state: Mapping[str, Any] = None, **kwargs) -> Iterable[Optional[Mapping[str, Any]]]:
        if not stream_state:
            stream_state = {}

        from_date = pendulum.parse(stream_state.get(self.cursor_field, self.sales_created_since))
        if from_date > pendulum.now():
            yield None
        else:
            yield {"UpdatedSince": from_date}

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None, start_date: str = None
    ) -> MutableMapping[str, Any]:

        params = { "limit": 1000 }

        if next_page_token:
            params.update(next_page_token)

        if stream_slice:
            params.update(stream_slice)

        return params

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        if response.json():
            total_records = response.json()["Total"]
            current_page = response.json()["Page"]

            if current_page < total_records / 1000:
                return {"page": current_page + 1}

        return None


    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        return response.json()["SaleList"]

class Products(Cin7CoreStream):
    primary_key = "ID"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "product"

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = { "limit": 1000, "IncludeDeprecated": "true" }

        if next_page_token:
            params.update(next_page_token)

        return params

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        if response.json():
            total_records = response.json()["Total"]
            current_page = response.json()["Page"]

            if current_page < total_records / 1000:
                return {"page": current_page + 1}

        return None


    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        return response.json()["Products"]

class ProductAvailability(Cin7CoreStream):
    primary_key = "ID"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "ref/productavailability"

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = { "limit": 1000 }

        if next_page_token:
            params.update(next_page_token)

        return params

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        if response.json():
            total_records = response.json()["Total"]
            current_page = response.json()["Page"]

            if current_page < total_records / 1000:
                return {"page": current_page + 1}

        return None


    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        return response.json()["ProductAvailabilityList"]


class SaleDetails(HttpSubStream, Sales):
    primary_key = "ID"
    cursor_field = "LastModifiedOn"

    def __init__(self, **kwargs):
        super().__init__(Sales(**kwargs), **kwargs)

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "sale"

    def stream_slices(self, sync_mode, stream_state: Mapping[str, Any] = None, **kwargs) -> Iterable[Optional[Mapping[str, Any]]]:
        if sync_mode == SyncMode.full_refresh:
            yield from super().stream_slices(stream_state, **kwargs)
        else:  # incremental sync
            for slice in super().stream_slices(stream_state, **kwargs):
                slice["LastModifiedOn"] = slice["parent"]["Updated"] # map parent Updated to LastModifiedOn
                if slice.get("LastModifiedOn") > stream_state.get(self.cursor_field, ""):
                    yield slice

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any], **kwargs
    ) -> MutableMapping[str, Any]:
        return { "ID": stream_slice["parent"]["SaleID"] }

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        return [response.json()]


class SaleCreditNotes(Cin7CoreStream):
    primary_key = "SaleID"

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "saleCreditNoteList"

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        params = { "limit": 1000 }

        if next_page_token:
            params.update(next_page_token)

        return params

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        if response.json():
            total_records = response.json()["Total"]
            current_page = response.json()["Page"]

            if current_page < total_records / 1000:
                return {"page": current_page + 1}

        return None


    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        return response.json()["SaleList"]


# Connnection class
# TODO: extract to own file
class Cin7TokenAuthenticator(AuthBase):
    """
    Builds header for token auth for Cin7 Core.
    """

    def __call__(self, request):
        """Attach the HTTP headers required to authenticate on the HTTP request"""
        request.headers.update(self.get_auth_header())
        return request

    def get_auth_header(self) -> Mapping[str, Any]:
        """HTTP header to set on the requests"""
        if self.auth_header:
            return self.auth_header
        return {}

    @property
    def auth_header(self) -> str:
        return self._auth_header

    def __init__(self, tokens):
        headers = {
                "api-auth-accountid": tokens["account_id"],
                "api-auth-applicationkey": tokens["api_key"],
        }
        self._auth_header = headers 


# Source
class SourceCin7Core(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        try:
            auth = Cin7TokenAuthenticator(config)
            stream = Customers(authenticator=auth)
            records = stream.read_records(sync_mode=SyncMode.full_refresh)
            next(records)
            return True, None
        except requests.exceptions.RequestException as e:
            return False, e

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        auth = Cin7TokenAuthenticator(config)
        return [
                Customers(authenticator=auth),
                Products(authenticator=auth),
                ProductAvailability(authenticator=auth),
                Sales(authenticator=auth, config=config),
                SaleDetails(config=config, authenticator=auth),
                SaleCreditNotes(authenticator=auth)
                ]
