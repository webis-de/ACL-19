**2023 Data Update:** Twitter API is defunct. 
Download the data directly: https://files.webis.de/data-in-progress/data-research/social-media-analysis/acl19-celebrity-profiling/
Download subsets: https://pan.webis.de/data.html?q=celebrity+profiling 

# Celebrity Profiling

This repository contains the data and code for reproducing results of the paper:

Matti Wiegmann, Benno Stein, and Martin Potthast. <a href="http://www.uni-weimar.de/medien/webis/publications/papers/stein_2018n.pdf" class="paper"><span class="title">Celebrity Profiling</span></a>. In <span class="booktitle">Proceedings of 57th Annual Meeting of the Association for Computational Linguistics (ACL 19)</span>, <span class="month">August</span> <span class="year">2019</span> 

### Repository Overview

In this repository you find:
  - [x] The dehydrated distribution version of our celebrity profiling corpus,
  - [x] Utilities to rehydrate this distribution,
  - [ ] The code to reproduce this corpus from scratch, and
  - [ ] The code to reproduce our experiments. 

In accordance with Twitters policy, we can not make our archived version available publicly and you have to acquire all tweets yourself again. If you need access to our archived version or have any other inquiries, please contact the corresponding authors:
  - Matti Wiegmann - matti.wiegmann[at]uni-weimar.de
  - Martin Potthast - martin.potthast[at]uni-leipzig.de

### Hydrating the Dataset

1. Unzip the distribution file. 
    ```bash
    ~$ unzip webis-celebrity-corpus-2019-distribution.ndjson.zip
    ```
      This file contains on each line the Twitter ID of a celebrity account and all respective Wikidata properties:
    ```json
    {"id": 21447363, 
     "labels": {
       "sex or gender (P21)": "female (Q6581072)",
       "genre (P136)": ["pop music (Q37073)", "rock music (Q11399)", "pop rock (Q484641)", ...], 
       "ethnic group (P172)": ["English American (Q1344183)", "German American (Q141817)", ...], 
       ...
       },
    }
    ```
2. Add your Twitter keys in the config.yml:
    ```yaml
    twitter_accounts:
      - consumer_key: "my-consumer-key"
        consumer_secret: "my-consumer-secret"
        access_key: "my-access-key"
        access_secret: "my-access-secret"

    ```
3. Install the requirements
    ```bash
    ~$ pip3 install -r requirements.txt
    ```
4. Run the hydrator:
    ```bash
    ~$ python3 hydrator.py 
    ```
    
