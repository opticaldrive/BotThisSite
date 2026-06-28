how ratelimits will work:
1. ratelimit the creation of new "names" in the database, per ip(v4/v6), asn/subnet if needed
2. ratelimit the amount of verifications a ip can send - but only counting failures. enforce basic length check. Exponential backoff(like the iphone thingy - ban for 10 years mwhahahaha /hj)
3. build caching service/file of last up-to-100k succesful tokens to prevent replays :(, ttl max 1 hr? idk