import hashlib
import json
import time
from typing import List, Dict

class HealthBlock:
    def __init__(self, index: int, data: Dict, previous_hash: str):
        self.index = index
        self.timestamp = time.time()
        self.data = data  # This is the anonymized health packet
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """
        Creates a unique digital fingerprint for this block.
        If even one number in the health data changes, the hash changes completely.
        """
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }, sort_keys=True).encode()
        
        return hashlib.sha256(block_string).hexdigest()

class CommunityLedger:
    def __init__(self):
        # The 'Genesis' block is the very first entry in our public ledger
        self.chain: List[HealthBlock] = [self.create_genesis_block()]

    def create_genesis_block(self) -> HealthBlock:
        return HealthBlock(0, {"message": "Global Health Commons Initiated"}, "0")

    def add_entry(self, anonymized_data: Dict) -> str:
        """
        Adds a new 'washed' health packet to the chain.
        """
        prev_block = self.chain[-1]
        new_block = HealthBlock(
            index=len(self.chain),
            data=anonymized_data,
            previous_hash=prev_block.hash
        )
        self.chain.append(new_block)
        return new_block.hash

    def get_average(self, metric_type: str) -> float:
        """
        The 'World Pulse' logic. Calculates the average of a metric 
        across the entire anonymous community.
        """
        relevant_values = [
            block.data["value"] 
            for block in self.chain 
            if isinstance(block.data, dict) and block.data.get("metric_type") == metric_type
        ]
        
        if not relevant_values:
            return 0.0
            
        return sum(relevant_values) / len(relevant_values)

# Initialize a single instance to be used across the app
global_ledger = CommunityLedger()
