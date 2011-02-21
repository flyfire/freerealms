from google.appengine.api import memcache
from google.appengine.ext import db
import random

class CounterShard(db.Model):
    count = db.IntegerProperty(required=True, default=0)

NUM_SHARDS = 20

def get_count():
    total = memcache.get('count', namespace='counter')
    if total is None:
        total = 0
        for counter in CounterShard.all():
            total += counter.count
        memcache.add('count', str(total), 60, namespace='counter')
    return total

def increment():
    def txn():
        index = random.randint(0, NUM_SHARDS - 1)
        shard_name = "shard%d" % index
        counter = CounterShard.get_by_key_name(shard_name)
        if counter is None:
            counter = CounterShard(key_name=shard_name)
        counter.count += 1
        counter.put()
    db.run_in_transaction(txn)
    memcache.incr('count', namespace='counter')

