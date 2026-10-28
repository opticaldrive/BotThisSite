how ratelimits will work:
1. ratelimit the creation of new "names" in the database, per ip(v4/v6), asn/subnet if needed - this touches stuff on the DB
2. ratelimit the amount of verifications a ip can send - but only counting failures. enforce basic length check. Exponential backoff(like the iphone thingy - ban for 10 years mwhahahaha /hj) (IMPORTANT #1 and #2 )
    2a. The number of failed verifications allowed should be low, as to not allow spamming to waste valuable quota of stuff likke hcaptcha and recaptcha. Maybe 10 failures/minute max or something to cooldown
    2b. We should also cap verifications per IP to some number or mitigate true load.
    2c. A current show of stress is cap.js
3. build caching service/file of last 2hrs of succesful tokens to prevent replays :(, ttl max 2 hr? idk (this is later cuz lazy)
    3a. Cap.js supposedly has ttl of 2 hr for tokens
4. zip bomb