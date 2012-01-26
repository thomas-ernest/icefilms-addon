#!/usr/bin/env python

# Links and info about metacontainers.
# Update this file to update the containers.

# Size is in MB

#return dictionary of strings and integers
def get():
          containers = {} 

          #date updated
          containers['date'] = 'Dec 2011'
          
          #--- Database Meta Container ---# 
          containers['db_url'] = 'https://rapidshare.com/files/743649507/video_cache.zip'
          containers['db_size'] = 11
                    
          #--- Movie Meta Container ---# 

          #basic container        
          containers['mv_covers_url'] = 'https://rapidshare.com/files/2789189937/movie_covers.zip'
          containers['mv_cover_size'] = 265
          
          containers['mv_backdrop_1_url'] = 'https://rapidshare.com/files/111604620/movie_backdrops1.zip'
          containers['mv_backdrop_2_url'] = 'https://rapidshare.com/files/2352819440/movie_backdrops2.zip'
          containers['mv_backdrop_3_url'] = 'https://rapidshare.com/files/2337530913/movie_backdrops3.zip'
          containers['mv_backdrop_size'] = 2600
          
          #--- TV   Meta  Container ---#

          #basic container       
          containers['tv_covers_url'] = 'https://rapidshare.com/files/779111945/tv_covers.zip'
          containers['tv_cover_size'] = 530

          containers['tv_banners_url'] = 'https://rapidshare.com/files/60134521/tv_banners.zip'
          containers['tv_banners_size'] = 175


          containers['tv_backdrop_url'] = 'https://rapidshare.com/files/1669815270/tv_backdrops.zip'
          containers['tv_backdrop_size'] = 832
          
          
          #additional container
          containers['tv_add_url'] = ''
          containers['tv_add_size'] = 0       


          return containers
