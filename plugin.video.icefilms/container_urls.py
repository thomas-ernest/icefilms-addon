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
          containers['db_url'] = 'http://www.2shared.com/file/kI9mnhlZ/video_cache.html'
          containers['db_size'] = 11
                    
          #--- Movie Meta Container ---# 

          #basic container        
          containers['mv_covers_url'] = 'http://www.2shared.com/file/6nuG38Vn/movie_covers.html'
          containers['mv_cover_size'] = 265
          
          containers['mv_backdrop_1_url'] = 'http://www.2shared.com/file/BhSTZsJS/movie_backdrops1.html'
          containers['mv_backdrop_2_url'] = 'http://www.2shared.com/file/ctm3lQLI/movie_backdrops2.html'
          containers['mv_backdrop_3_url'] = 'http://www.2shared.com/file/KGVP9scV/movie_backdrops3.html'
          containers['mv_backdrop_size'] = 2600
          
          #--- TV   Meta  Container ---#

          #basic container       
          containers['tv_covers_url'] = 'http://www.2shared.com/file/6fPgfIjH/tv_covers.html'
          containers['tv_cover_size'] = 530

          containers['tv_banners_url'] = 'http://www.2shared.com/file/JV2mFfRx/tv_banners.html'
          containers['tv_banners_size'] = 175


          containers['tv_backdrop_url'] = 'http://www.2shared.com/file/de060K2m/tv_backdrops.html'
          containers['tv_backdrop_size'] = 832
          
          
          #additional container
          containers['tv_add_url'] = ''
          containers['tv_add_size'] = 0       


          return containers
