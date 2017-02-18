# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 20:31:48 2017

@author: Jake
"""
import requests
from pymongo import MongoClient
import time
from datetime import datetime
from pandas import DataFrame


class RecommendBot():
    
    def __init__(self):
        
        # Base of all api calls
        self.base = "http://www.reddit.com/"

        # Default "after" keyword; defaults at blank string
        self.after = ""     
        
        # ID associated with client APP
        self.client_id = 'z9qkMgxsHyIcHA'
        # Secret hash for authentication with reddit api
        self.client_secret = 'gsZe-zO1Lo6fIwa2UilXWUWXu_s'
        
        self.access_token = self.authentication()
        
        # Keep track of when the last API call was made
        self.lastCall = 0
        
        # MongoDB client
        self.client = MongoClient()
        
    def authentication(self):
        
        # requesting access token from reddit api (to allow us to gather data)
        self.client_auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)

        # Data for signing in to our account
        self.post_data = {"grant_type": "password", "username": "SubRecommendBot", 
                     "password": "channel5"}

        # Description of your app
        self.headers = {"User-Agent": "Script bot for testing data collection by SubRecommendBot"}
 
    def checkAPITime(self, link):
        # Make sure the call returned the data we want, otherwise
        # try to make the call again
        userInfo = {}
        sleep = 0
        errorBool = False
        while 'data' not in userInfo.keys():  
            time.sleep(sleep)
            response = requests.post(link, auth=self.client_auth, data=self.post_data, headers=self.headers)
            self.lastCall = time.time()
            userInfo = response.json()
            sleep = 2
            
            # if user has deleted their account, skip user
            if 'error' in userInfo.keys():
                if userInfo['error'] == 404:
                    errorBool = True
                    break
        
        userInfo['404Error'] = errorBool
        return userInfo
       
    def getNewUsers(self, limit=25):
        
        # Reset after keyword if needed
        if self.after != "":
            self.after = ""
            
        userList = []
        
        while True:
            
            # Make sure not to exceed 100 for limit
            if limit > 100:
                currentLimit = 100
            else:
                currentLimit = limit
            
            # Construct keyword part of link
            keywords = "limit={limit}&after={after}".format(limit=currentLimit, after=self.after)
            
            # Link contruction for r/new
            link = self.base + "new/.json?" + keywords
            userInfo = self.checkAPITime(link)

            
            # return author of posts to r/new
            
            for user in range(len(userInfo['data']['children'])):
                userList.append(userInfo['data']['children'][user]['data']['author'])
            
            
            # Do not make too many calls to the API
            if limit > 0:
                waitCheck = time.time() - self.lastCall
                # Make Sure 2 Seconds have passed since last call
                while(waitCheck < 2):
                    waitCheck = time.time() - self.lastCall
                # Adjust limit
                limit -= 100  
                self.after = userInfo['data']['after']
            
            else:  
                return userList
    
    
    # this function works with getNewUsers, it needs to return both the redditors
    # username and the comments associated with that user    
    def getUserCommentSubs(self, userLimit=25, subLimit=25):
        
        print('retrieving users...')
        authors = self.getNewUsers(userLimit)
        print('retrieving subs...')
        # Dic of Key User and Value Subreddit
        userSubs = []
        allSubs = []
        
        # Remember original Limit
        originalLimit = subLimit        
        
        # Make API call for each author
        for author in authors:
            print(author)
            # Subreddit list as value for userSubs
            subs = []
            
            # Reset after keyword if needed
            if self.after != "":
                self.after = ""
                
            while True:
                
                # Make sure not to exceed 100 for limit
                if subLimit > 100:
                    currentLimit = 100
                else:
                    currentLimit = subLimit

    
                # Construct keyword part of link
                keywords = "limit={limit}&after={after}".format(limit=currentLimit, after=self.after)
                
                # Link construction for user comments
                link = self.base + "user/{username}/comments/.json?".format(username=author)
                link += keywords
                
                subInfo = self.checkAPITime(link)
                
                if subInfo['404Error']:
#                    RecommendBot.deleteUserFromDB(author[0]) 
                    break
                    
                for i in range(len(subInfo['data']['children'])):
                    subs.append(subInfo['data']['children'][i]['data']['subreddit'])
                    allSubs.append(subInfo['data']['children'][i]['data']['subreddit'])
                    
                self.after = subInfo['data']['after']
                    
                # Do not make too many calls to the API
                if subLimit > 0 and self.after != None:
                    waitCheck = time.time() - self.lastCall
                    # Make Sure 2 Seconds have passed since last call
                    while(waitCheck < 2):
                        waitCheck = time.time() - self.lastCall
                    # Adjust limit
                    subLimit -= 100  
                    
                else:
                    
                    if len(subs) > 0:

                        user = {"username": author,
                            "subreddit": list(set(subs)),
                            "update": datetime.now()
                            }                    
                    
                        userSubs.append(user)
                    
                    # Reset Limit for next author
                    subLimit = originalLimit
                    break
        print('Done with retrieving comments!') 

        print('commiting to database')
        
        for user in userSubs:
            self.commitUserToDB(user)
            
        for sub in set(allSubs):
            self.commitSubToDB(sub)
        print('Done!')
        
               
    def commitUserToDB(self, user):

        db = self.client.subRec
        collection = db.users
        userID = collection.update({'username':user['username']}, user, upsert=True)
        return userID
        
    
    def commitSubToDB(self, subreddit):
        
        db = self.client.subRec
        collection = db.subs
        userID = collection.update(
            {'name' : subreddit}, 
            {'name': subreddit, 'updated': datetime.now()}, upsert=True)
            
        return userID
        
    @staticmethod
    def updateDB(username, subreddits):
        client = RecommendBot.createClient()
        collection = client.subRec.users
        collection.update({'username' : username}, {'$set': {'subreddits' : subreddits}})
        
        
    def userVectors(self, client):
        # return a one hot dataframe with subreddit as column and user as row
        redditors = [redditor['username'] for redditor in self.client.subRec.users.find()]
        subs = [sub['name'] for sub in self.client.subRec.subs.find()]
        df = DataFrame(0, index=redditors, columns= subs)
        for user in self.client.subRec.users.find():
            df = df.set_value(user['username'], user['subreddit'], 1)
        return df
        
        
        