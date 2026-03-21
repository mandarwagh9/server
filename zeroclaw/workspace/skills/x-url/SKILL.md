---
name: x-url
version: 1.0.0
description: Post, read, search, and interact with X (Twitter) using the official xurl CLI tool. Use when: (1) User wants to post a tweet, (2) User wants to read/search tweets, (3) User wants to reply, quote, like, or repost, (4) User wants to check their timeline or mentions.
tags: [x, twitter, social-media, posting]
---

# X (Twitter) — xurl

Post and interact with X using the `xurl` CLI tool.

## Setup

First, authenticate with X API credentials. You need:
1. **API Key** and **API Secret** (from [developer.twitter.com](https://developer.twitter.com))
2. **Bearer Token** (for read operations)

```bash
# Authenticate with OAuth1 (for posting)
xurl auth apps add my-app --client-id YOUR_API_KEY --client-secret YOUR_API_SECRET
xurl auth default my-app
xurl --auth oauth1 post "Hello from ZeroClaw!"
```

## Commands

| Action | Command |
|--------|---------|
| Post tweet | `xurl post "your message"` |
| Reply | `xurl reply TWEET_ID "your reply"` |
| Quote tweet | `xurl quote TWEET_ID "your comment"` |
| Read tweet | `xurl read TWEET_ID` |
| Search | `xurl search "query" -n 10` |
| Timeline | `xurl timeline` |
| Mentions | `xurl mentions` |
| Like | `xurl like TWEET_ID` |
| Repost | `xurl repost TWEET_ID` |
| Follow | `xurl follow @username` |
| Send DM | `xurl dm @username "message"` |
| My profile | `xurl whoami` |
| Delete tweet | `xurl delete TWEET_ID` |

## Notes

- For posting/replying: use OAuth1 auth (`--auth oauth1`)
- For reading/searching: use Bearer token auth (`--auth app`)
- Tweet IDs can be extracted from full URLs (e.g. `https://x.com/user/status/123456` → ID is `123456`)
- Rate limits apply — space out bulk operations
- Always confirm with user before posting, liking, or retweeting
