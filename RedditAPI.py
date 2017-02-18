# -*- coding: utf-8 -*-
"""
Created on Sat Feb 18 13:48:35 2017

@author: Jake Fortner
"""

import requests
import time

class Reddit(object):
    
    def __init__(self):
        
        # Base of all api calls
        self.base = "http://www.reddit.com/"

        # Default "after" keyword; defaults at blank string
        self.after = ""     
        
        # Get our Client ID and Client Secret from file labeled 'credentials.txt'
        f = open("credentials.txt", "r")
        
        # ID associated with client APP
        self.client_id = f.readline()
        
        # Secret hash for authentication with reddit api
        self.client_secret = f.readline()
        
        # Close file object
        f.close()
        
        # Originally for gather Access Toke; has caused errors before though,
        # so temporarily does nothing.
        self._authentication()
        
        # Keep track of when the last API call was made
        self.lastCall = 0
        
    
    def _authentication(self):
        """
        Authenticates with the API and returns access token (if needed)
        """
        
        # requesting access token from reddit api (to allow us to gather data)
        self.client_auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)

        # Data for signing in to our account
        self.post_data = {"grant_type": "password", "username": "SubRecommendBot", 
                     "password": "channel5"}

        # Description of your app
        self.headers = {"User-Agent": "Script bot for testing data collection by SubRecommendBot"}
        

    def _makeCall(self, link):
        """
        Makes the API call and makes sure the call returned the data we want, 
        otherwise try to make the call again
        """
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
        
        
    def checkLastCall(self):
        """
        Checks if the last API call was 2 seconds ago; If yes, returns TRUE,
        If no, returns FALSE
        """
        if time.time() - self.lastCall > 2:
            return True
        
        return False
        
        
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
            userInfo = self._makeCall(link)

            
            # return author of posts to r/new
            for user in range(len(userInfo['data']['children'])):
                userList.append(userInfo['data']['children'][user]['data']['author'])
            
            
            # Do not make too many calls to the API
            if limit > 0:
                # Make Sure 2 Seconds have passed since last call
                while(self.checkLastCall()):
                    # Wait it out
                
                # Adjust limit
                limit -= 100  
                self.after = userInfo['data']['after']
            
            else:  
                return userList
                
                
        
    def getUserCommentSubs(self, userLimit=25, subLimit=25):
        """
        This function works with getNewUsers, it needs to return both the redditors
        username and the subs associated with that user
        """
        
        print('Retrieving users...')
        authors = self.getNewUsers(userLimit)
        print('Retrieving subs...')
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
                
                subInfo = self._makeCall(link)
                
                if subInfo['404Error']:
                    break
                    
                for i in range(len(subInfo['data']['children'])):
                    subs.append(subInfo['data']['children'][i]['data']['subreddit'])
                    allSubs.append(subInfo['data']['children'][i]['data']['subreddit'])
                    
                self.after = subInfo['data']['after']
                    
                # Do not make too many calls to the API
                if subLimit > 0 and self.after != None:
                    # Make Sure 2 Seconds have passed since last call
                    while(self.checkLasCall()):
                        # Wait it out                        
                        
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
        
        return userSubs, set(allSubs)
        
    
    
    