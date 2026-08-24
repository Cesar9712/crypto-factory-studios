from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable
from ..models import TransferEvent

class TronProvider(ABC):
    @abstractmethod
    def get_transfer(self, txid:str, event_index:int=0): ...
    @abstractmethod
    def incoming_transfers(self, address:str): ...
    @abstractmethod
    def health_check(self)->bool: ...

class MockTronProvider(TronProvider):
    def __init__(self): self.transfers={}; self.available=True
    def add_transfer(self,event:TransferEvent): self.transfers[event.unique_key()]=event
    def get_transfer(self,txid,event_index=0): return self.transfers.get(f'{txid}:{event_index}')
    def incoming_transfers(self,address): return [t for t in self.transfers.values() if t.to_address==address]
    def health_check(self): return self.available
