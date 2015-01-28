import xbmc,xbmcgui
import os
import urllib, urllib2
import cookielib
import re
import jsunpack

''' Use addon.common library for http calls '''
from addon.common.net import Net
from addon.common.addon import Addon
net = Net()

addon = Addon('plugin.video.icefilms')
datapath = addon.get_profile()

cookie_path = os.path.join(datapath, 'cookies')

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.72 Safari/537.36'
ACCEPT = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

def handle_captchas(url, html, data, dialog):

    headers = {'Referer': url}

    puzzle_img = os.path.join(datapath, "solve_puzzle.png")
    
    #Check for type of captcha used
    solvemedia = re.search('<iframe src="(http://api.solvemedia.com.+?)"', html)
    recaptcha = re.search('<script type="text/javascript" src="(http://www.google.com.+?)">', html)
    numeric_captcha = re.compile("left:(\d+)px;padding-top:\d+px;'>&#(.+?);<").findall(html)    

    #SolveMedia captcha
    if solvemedia:
       dialog.close()
       html = net.http_GET(solvemedia.group(1), headers=headers).content
       hugekey=re.search('id="adcopy_challenge" value="(.+?)">', html).group(1)
       
       #Check for alternate puzzle type - stored in a div
       alt_puzzle = re.search('<div><iframe src="(/papi/media.+?)"', html)
       if alt_puzzle:
           open(puzzle_img, 'wb').write(net.http_GET("http://api.solvemedia.com%s" % alt_puzzle.group(1)).content)
       else:
           open(puzzle_img, 'wb').write(net.http_GET("http://api.solvemedia.com%s" % re.search('<img src="(/papi/media.+?)"', html).group(1)).content)
       
       img = xbmcgui.ControlImage(450,15,400,130, puzzle_img)
       wdlg = xbmcgui.WindowDialog()
       wdlg.addControl(img)
       wdlg.show()
    
       xbmc.sleep(3000)

       kb = xbmc.Keyboard('', 'Type the letters in the image', False)
       kb.doModal()
       capcode = kb.getText()

       if (kb.isConfirmed()):
           userInput = kb.getText()
           if userInput != '':
               solution = kb.getText()
           elif userInput == '':
               raise Exception ('You must enter text in the image to access video')
       else:
           wdlg.close()
           raise Exception ('Captcha Error')
       wdlg.close()
       data.update({'adcopy_challenge': hugekey,'adcopy_response': solution})

    #Google Recaptcha
    elif recaptcha:
        dialog.close()
        html = net.http_GET(recaptcha.group(1), headers=headers).content
        part = re.search("challenge \: \\'(.+?)\\'", html)
        captchaimg = 'http://www.google.com/recaptcha/api/image?c='+part.group(1)
        img = xbmcgui.ControlImage(450,15,400,130,captchaimg)
        wdlg = xbmcgui.WindowDialog()
        wdlg.addControl(img)
        wdlg.show()

        xbmc.sleep(3000)

        kb = xbmc.Keyboard('', 'Type the letters in the image', False)
        kb.doModal()
        capcode = kb.getText()

        if (kb.isConfirmed()):
            userInput = kb.getText()
            if userInput != '':
                solution = kb.getText()
            elif userInput == '':
                raise Exception ('You must enter text in the image to access video')
        else:
            wdlg.close()
            raise Exception ('Captcha Error')
        wdlg.close()
        data.update({'recaptcha_challenge_field':part.group(1),'recaptcha_response_field':solution})               

    #Numeric captcha - we can programmatically figure this out
    elif numeric_captcha:
        result = sorted(numeric_captcha, key=lambda ltr: int(ltr[0]))
        solution = ''.join(str(int(num[1])-48) for num in result)
        data.update({'code':solution})  
        
    return data


def resolve_180upload(url):

    try:
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving 180Upload Link...')
        dialog.update(0)
        
        media_id = re.search('//.+?/([\w]+)', url).group(1)
        web_url = 'http://180upload.com/embed-%s.html' % media_id
       
        addon.log_debug( '180Upload - Requesting GET URL: %s' % web_url)
        html = net.http_GET(web_url).content

        dialog.update(50)

        wrong_captcha = True
        
        while wrong_captcha:
        
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)"', html)

            if r:
                for name, value in r:
                    data[name] = value
            else:
                raise Exception('Unable to resolve 180Upload Link')

            # 1st attempt, probably no captcha
            addon.log('180Upload - Requesting POST URL: %s Data values: %s' % (web_url, data))
            html = net.http_POST(web_url, data).content
 
            packed = re.search('id="player_code".*?(eval.*?\)\)\))', html,re.DOTALL)
            if packed:
                js = jsunpack.unpack(packed.group(1))
                link = re.search('name="src"0="([^"]+)"/>', js.replace('\\',''))
                if link:
                    addon.log('180Upload Link Found: %s' % link.group(1))
                    dialog.update(100)
                    return link.group(1)
                else:
                    link = re.search("'file','(.+?)'", js.replace('\\',''))
                    if link:
                        addon.log('180Upload Link Found: %s' % link.group(1))
                        return link.group(1)                    
                    
            #Cannot get video without captcha, so try regular url
            html = net.http_GET(url).content

            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)

            if r:
                for name, value in r:
                    data[name] = value
            else:
                raise Exception('Unable to resolve 180Upload Link')            
            
            #Check for captcha
            data = handle_captchas(url, html, data, dialog)

            dialog.create('Resolving', 'Resolving 180Uploads Link...') 
            dialog.update(50)  
            
            addon.log_debug( '180Upload - Requesting POST URL: %s Data: %s' % (url, data))
            html = net.http_POST(url, data).content

            wrong_captcha = re.search('<div class="err">Wrong captcha</div>', html)
            if wrong_captcha:
                addon.show_ok_dialog(['Wrong captcha entered, try again'], title='Wrong Captcha', is_error=False)

        dialog.update(100)
        
        link = re.search('id="lnk_download" href="([^"]+)', html)
        if link:
            addon.log_debug( '180Upload Link Found: %s' % link.group(1))
            return link.group(1)
        else:
            raise Exception('Unable to resolve 180Upload Link')

    except Exception, e:
        addon.log_error('**** 180Upload Error occured: %s' % e)
        raise
    finally:
        dialog.close()


def resolve_megafiles(url):

    try:
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving MegaFiles Link...')
        dialog.update(0)
        
        addon.log_debug('MegaFiles - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content

        dialog.update(50)

        wrong_captcha = True
        
        while wrong_captcha:
        
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)

            if r:
                for name, value in r:
                    data[name] = value
            else:
                raise Exception('Unable to resolve MegaFiles Link')

            #Handle captcha
            data = handle_captchas(url, html, data, dialog)

            dialog.create('Resolving', 'Resolving MegaFiles Link...') 
            dialog.update(50)                  

            addon.log_debug('MegaFiles - Requesting POST URL: %s' % url)
            html = net.http_POST(url, data).content

            wrong_captcha = re.search('<div class="err">Wrong captcha</div>', html)
            if wrong_captcha:
                addon.show_ok_dialog(['Wrong captcha entered, try again'], title='Wrong Captcha', is_error=False)
            
        dialog.update(100)
        
        link = re.search("var download_url = '(.+?)';", html)
        if link:
            addon.log_debug('MegaFiles Link Found: %s' % link.group(1))
            return link.group(1)
        else:
            raise Exception('Unable to resolve MegaFiles Link')

    except Exception, e:
        addon.log_error('**** MegaFiles Error occured: %s' % e)
        raise
    finally:
        dialog.close()
        

def resolve_vidhog(url):

    try:
        
        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving VidHog Link...')
        dialog.update(0)
        
        addon.log_debug('VidHog - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content

        dialog.update(50)
        
        #Check page for any error msgs
        if re.search('This server is in maintenance mode', html):
            raise Exception('File is currently unavailable on the host')
        if re.search('<b>File Not Found</b>', html):
            raise Exception('File has been deleted')

        filename = re.search('<strong>\(<font color="red">(.+?)</font>\)</strong><br><br>', html).group(1)
        extension = re.search('(\.[^\.]*$)', filename).group(1)
        guid = re.search('http://vidhog.com/(.+)$', url).group(1)
        
        vid_embed_url = 'http://vidhog.com/vidembed-%s%s' % (guid, extension)
        
        request = urllib2.Request(vid_embed_url)
        request.add_header('User-Agent', USER_AGENT)
        request.add_header('Accept', ACCEPT)
        request.add_header('Referer', url)
        response = urllib2.urlopen(request)
        redirect_url = re.search('(http://.+?)video', response.geturl()).group(1)
        download_link = redirect_url + filename
        
        dialog.update(100)

        return download_link
        
    except Exception, e:
        addon.log_error('**** VidHog Error occured: %s' % e)
        raise
    finally:
        dialog.close()

        
def resolve_vidplay(url):

    try:
        
        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving VidPlay Link...')
        dialog.update(0)
        
        addon.log_debug('VidPlay - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content

        dialog.update(50)
        
        #Check page for any error msgs
        if re.search('This server is in maintenance mode', html):
            raise Exception('File is currently unavailable on the host')
        if re.search('<b>File Not Found</b>', html):
            raise Exception('File has been deleted')

        filename = re.search('<h4>(.+?)</h4>', html).group(1)
        extension = re.search('(\.[^\.]*$)', filename).group(1)
        guid = re.search('http://vidplay.net/(.+)$', url).group(1)
        
        vid_embed_url = 'http://vidplay.net/vidembed-%s%s' % (guid, extension)
        
        request = urllib2.Request(vid_embed_url)
        request.add_header('User-Agent', USER_AGENT)
        request.add_header('Accept', ACCEPT)
        request.add_header('Referer', url)
        response = urllib2.urlopen(request)
        redirect_url = re.search('(http://.+?)video', response.geturl()).group(1)
        download_link = redirect_url + filename
        
        dialog.update(100)

        return download_link
        
    except Exception, e:
        addon.log_error('**** VidPlay Error occured: %s' % e)
        raise
    finally:
        dialog.close()
        

def resolve_movreel(url):

    try:

        if addon.get_setting('movreel-account') == 'true':
            addon.log('MovReel - Setting Cookie file')
            cookiejar = os.path.join(cookie_path,'movreel.lwp')
            net.set_cookies(cookiejar)

        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving Movreel Link...')       
        dialog.update(0)
        
        addon.log('Movreel - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content
        
        dialog.update(50)
        
        #Check page for any error msgs
        if re.search('This server is in maintenance mode', html):
            addon.log_error('***** Movreel - Site reported maintenance mode')
            raise Exception('File is currently unavailable on the host')

        #Set POST data values
        data = {}
        r = re.findall('type="hidden" name="(.+?)" value="(.+?)">', html)
        if r:
            for name, value in r:
                data[name] = value
        
        wait_time = re.search('<span id="countdown_str">Wait <span id=".+?">(.+?)</span> seconds</span>', html)
        if wait_time:
            addon.log('Wait time found: %s' % wait_time.group(1))
            xbmc.sleep(int(wait_time.group(1)) * 1000)
        
        addon.log('Movreel - Requesting POST URL: %s DATA: %s' % (url, data))
        html = net.http_POST(url, data).content

        #Get download link
        dialog.update(100)
        link = re.search('<a href="(.+)">Download Link</a>', html)
        if link:
            return link.group(1)
        else:
            raise Exception("Unable to find final link")

    except Exception, e:
        addon.log_error('**** Movreel Error occured: %s' % e)
        raise
    finally:
        dialog.close()


def resolve_billionuploads(url):

    try:

        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving BillionUploads Link...')       
        dialog.update(0)
        
        addon.log('BillionUploads - Requesting GET URL: %s' % url)
        
        headers = {
                   'Host': 'billionuploads.com'
                }
        
        tries = 0
        MAX_TRIES = 3
        
        r = re.search('[^/]+(?=/$|$)', url)
        if r:
            url = 'http://www.billionuploads.com/%s' % r.group(0)

        def __incapsala_decode(s):
            return s.decode('hex')          

        while tries < MAX_TRIES:
            html = net.http_GET(url, headers=headers).content
            dialog.update(50)
        
            match=re.search('var\s+b\s*=\s*"([^"]+)', html)
            if match:
                html = __incapsala_decode(match.group(1))
                match = re.search(',\s*"(/_Incapsula[^"]+)', html)
                incap_url = 'http://www.billionuploads.com' + match.group(1)
                net.http_GET(incap_url, headers=headers) # Don't need content, just the cookies
            else:
                # Even though a captcha can be returned, it seems not to be required if you just re-request the page
                match = re.search('iframe\s+src="(/_Incapsula[^"]+)', html)
                if match:
                    captcha_url = 'http://www.billionuploads.com' + urllib.quote(match.group(1))
                    html = net.http_GET(captcha_url, headers=headers).content
                else:
                    # not a Incapsula or a Captcha, so probably the landing page
                    break
            
            tries = tries + 1
        else:
            raise Exception('Tries Ran Out')
        
        if re.search('>\s*File Not Found\s*<', html, re.I):
            raise Exception('File Not Found/Removed')

        data = {}
        r = re.findall(r'type="hidden"\s+name="(.+?)"\s+value="(.*?)"', html)
        for name, value in r: data[name] = value
        data['method_free']='Download or watch'

        html = net.http_POST(url, form_data = data, headers = headers).content
        
        dialog.update(100)
        r = re.search(r'class="[^"]*download"\s+href="([^"]+)', html)
        if r:
            return r.group(1)
        else:
            raise Exception('Unable to locate file link')
    
    except Exception, e:
        addon.log_error('**** BillionUploads Error occured: %s' % e)
        raise
    finally:
        dialog.close()


def resolve_epicshare(url):

    try:
        
        puzzle_img = os.path.join(datapath, "epicshare_puzzle.png")
        
        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving EpicShare Link...')
        dialog.update(0)
        
        addon.log('EpicShare - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content

        dialog.update(50)
        
        #Check page for any error msgs
        if re.search('This server is in maintenance mode', html):
            addon.log_error('***** EpicShare - Site reported maintenance mode')
            raise Exception('File is currently unavailable on the host')
        if re.search('<b>File Not Found</b>', html):
            addon.log_error('***** EpicShare - File not found')
            raise Exception('File has been deleted')

        wrong_captcha = True
        
        while wrong_captcha:
        
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)

            if r:
                for name, value in r:
                    data[name] = value
            else:
                addon.log_error('***** EpicShare - Cannot find data values')
                raise Exception('Unable to resolve EpicShare Link')

            #Handle captcha
            data = handle_captchas(url, html, data, dialog)
            
            dialog.create('Resolving', 'Resolving EpicShare Link...') 
            dialog.update(50) 
                
            addon.log('EpicShare - Requesting POST URL: %s' % url)
            html = net.http_POST(url, data).content

            wrong_captcha = re.search('<div class="err">Wrong captcha</div>', html)
            if wrong_captcha:
                addon.show_ok_dialog(['Wrong captcha entered, try again'], title='Wrong Captcha', is_error=False)            
        
        dialog.update(100)
        
        link = re.search('product_download_url=(.+?)"', html)
        if link:
            addon.log('EpicShare Link Found: %s' % link.group(1))
            return link.group(1)
        else:
            addon.log_error('***** EpicShare - Cannot find final link')
            raise Exception('Unable to resolve EpicShare Link')
        
    except Exception, e:
        addon.log_error('**** EpicShare Error occured: %s' % e)
        raise

    finally:
        dialog.close()


def resolve_megarelease(url):

    try:
        
        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving MegaRelease Link...')
        dialog.update(0)
        
        addon.log('MegaRelease - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content

        dialog.update(50)
        
        #Check page for any error msgs
        if re.search('This server is in maintenance mode', html):
            addon.log_error('***** MegaRelease - Site reported maintenance mode')
            raise Exception('File is currently unavailable on the host')
        if re.search('<b>File Not Found</b>', html):
            addon.log_error('***** MegaRelease - File not found')
            raise Exception('File has been deleted')

        filename = re.search('You have requested <font color="red">(.+?)</font>', html).group(1)
        filename = filename.split('/')[-1]
        extension = re.search('(\.[^\.]*$)', filename).group(1)
        guid = re.search('http://megarelease.org/(.+)$', url).group(1)
        
        vid_embed_url = 'http://megarelease.org/vidembed-%s%s' % (guid, extension)
        
        request = urllib2.Request(vid_embed_url)
        request.add_header('User-Agent', USER_AGENT)
        request.add_header('Accept', ACCEPT)
        request.add_header('Referer', url)
        response = urllib2.urlopen(request)
        redirect_url = re.search('(http://.+?)video', response.geturl()).group(1)
        download_link = redirect_url + filename
        
        dialog.update(100)

        return download_link
        
    except Exception, e:
        addon.log_error('**** MegaRelease Error occured: %s' % e)
        raise
    finally:
        dialog.close()


def resolve_hugefiles(url):

    try:

        puzzle_img = os.path.join(datapath, "hugefiles_puzzle.png")
        
        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving HugeFiles Link...')       
        dialog.update(0)
        
        addon.log('HugeFiles - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content
        
        dialog.update(50)
        
        #Check page for any error msgs
        if re.search('<h3>File Not found</h3>', html):
            addon.log_error('***** HugeFiles - File Not Found')
            raise Exception('File Not Found')

        wrong_captcha = True
        
        while wrong_captcha:
        
            #Set POST data values
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
            
            if r:
                for name, value in r:
                    data[name] = value
            else:
                addon.log_error('***** HugeFiles - Cannot find data values')
                raise Exception('Unable to resolve HugeFiles Link')
            
            data['method_free'] = 'Free Download'

            #Handle captcha
            data = handle_captchas(url, html, data, dialog)
            
            dialog.create('Resolving', 'Resolving HugeFiles Link...') 
            dialog.update(50)             
            
            addon.log('HugeFiles - Requesting POST URL: %s DATA: %s' % (url, data))
            html = net.http_POST(url, data).content

            solvemedia = re.search('<iframe src="(http://api.solvemedia.com.+?)"', html)
            recaptcha = re.search('<script type="text/javascript" src="(http://www.google.com.+?)">', html)
            numeric_captcha = re.compile("left:(\d+)px;padding-top:\d+px;'>&#(.+?);<").findall(html)   

            if solvemedia or recaptcha or numeric_captcha:
                addon.show_ok_dialog(['Wrong captcha entered, try again'], title='Wrong Captcha', is_error=False)
            else:
                wrong_captcha = False
            
        # issue one more time for download link
        #Set POST data values
        data = {}
        r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
        
        if r:
            for name, value in r:
                data[name] = value
        else:
            common.addon.log('***** HugeFiles - Cannot find data values')
            raise Exception('Unable to resolve HugeFiles Link')
        data['method_free'] = 'Free Download'

        # can't use t0mm0 net because the post doesn't return until the file is downloaded
        request = urllib2.Request(url, urllib.urlencode(data))
        response = urllib2.urlopen(request)

        #Get download link
        dialog.update(100)
        
        stream_url = response.geturl()
        
        # assume that if the final url matches the original url that the process failed
        if stream_url == url:
            raise Exception('Unable to find stream url')
        return stream_url        
        
    except Exception, e:
        addon.log_error('**** HugeFiles Error occured: %s' % e)
        raise
    finally:
        dialog.close()


def resolve_entroupload(url):

    try:

        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving EntroUpload Link...')       
        dialog.update(0)
        
        addon.log('EntroUpload - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content
        
        dialog.update(50)
        
        #Check page for any error msgs
        if re.search('<b>File Not Found</b>', html):
            addon.log_error('***** EntroUpload - File Not Found')
            raise Exception('File Not Found')

        #Set POST data values
        data = {}
        r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
        
        if r:
            for name, value in r:
                data[name] = value
        else:
            addon.log_error('***** EntroUpload - Cannot find data values')
            raise Exception('Unable to resolve EntroUpload Link')
        
        data['method_free'] = 'Free Download'
        file_name = data['fname']

        addon.log('EntroUpload - Requesting POST URL: %s DATA: %s' % (url, data))
        html = net.http_POST(url, data).content

        #Get download link
        dialog.update(100)

        sPattern =  '<script type=(?:"|\')text/javascript(?:"|\')>(eval\('
        sPattern += 'function\(p,a,c,k,e,d\)(?!.+player_ads.+).+np_vid.+?)'
        sPattern += '\s+?</script>'
        r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)
        if r:
            sJavascript = r.group(1)
            sUnpacked = jsunpack.unpack(sJavascript)
            sPattern  = '<embed id="np_vid"type="video/divx"src="(.+?)'
            sPattern += '"custommode='
            r = re.search(sPattern, sUnpacked)
            if r:
                return r.group(1)
            else:
                addon.log_error('***** EntroUpload - Cannot find final link')
                raise Exception('Unable to resolve EntroUpload Link')
        else:
            addon.log_error('***** EntroUpload - Cannot find final link')
            raise Exception('Unable to resolve EntroUpload Link')
        
    except Exception, e:
        addon.log_error('**** EntroUpload Error occured: %s' % e)
        raise
    finally:
        dialog.close()


def resolve_donevideo(url):

    try:

        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving DoneVideo Link...')       
        dialog.update(0)
        
        addon.log('DoneVideo - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content
    
        data = {}
        r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
        
        if r:
          for name, value in r:
              data[name] = value
        else:
            addon.log_error('***** DoneVideo - Cannot find data values')
            raise Exception('Unable to resolve DoneVideo Link')
        
        data['method_free'] = 'Continue to Video'
        addon.log('DoneVideo - Requesting POST URL: %s' % url)
        
        html = net.http_POST(url, data).content
        
        dialog.update(50)
                
        r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
        
        if r:
          for name, value in r:
              data[name] = value
        else:
          addon.log_error('Could not resolve link')
        
        data['method_free'] = 'Continue to Video'
        
        addon.log('DoneVideo - Requesting POST URL: %s' % url)
        
        html = net.http_POST(url, data).content

        #Get download link
        dialog.update(100)
        
        sPattern = '''<div id="player_code">.*?<script type='text/javascript'>(eval.+?)</script>'''
        r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)

        if r:
          sJavascript = r.group(1)
          sUnpacked = jsunpack.unpack(sJavascript)
          sUnpacked = sUnpacked.replace("\\","")
                   
        r = re.search("addVariable.+?'file','(.+?)'", sUnpacked)
                
        if r:
            return r.group(1)
        else:
            sPattern  = '<embed id="np_vid"type="video/divx"src="(.+?)'
            sPattern += '"custommode='
            r = re.search(sPattern, sUnpacked)
            if r:
                return r.group(1)
            else:
                addon.log_error('***** DoneVideo - Cannot find final link')
                raise Exception('Unable to resolve DoneVideo Link')

    except Exception, e:
        addon.log_error('**** DoneVideo Error occured: %s' % e)
        raise
    finally:
        dialog.close()


def resolve_360gig(url):

    try:

        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving 360Gig Link...')       
        dialog.update(0)
        
        addon.log('360Gig - Requesting GET URL: %s' % url)
        html = net.http_GET(url).content

        #Check page for any error msgs
        if re.search('<b>File Not Found</b><br><br>', html):
            print '***** 360Gig - File Not Found'
            raise Exception('File Not Found')
    
        data = {}
        r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
        
        if r:
          for name, value in r:
              data[name] = value
        else:
            addon.log_error('***** 360Gig - Cannot find data values')
            raise Exception('Unable to resolve 360Gig Link')
        
        data['method_free'] = 'STANDARD DOWNLOAD'
        data['referer'] = url
        
        addon.log('360Gig - Requesting POST URL: %s' % url)
        
        html = net.http_POST(url, data).content
        
        dialog.update(50)
        
        data = {}        
        r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
        
        if r:
          for name, value in r:
              data[name] = value
        else:
          addon.log_error('Could not resolve link')
        
        data['method_free'] = 'STANDARD DOWNLOAD'
        data['referer'] = url
        
        addon.log('360Gig - Requesting POST URL: %s' % url)
        
        html = net.http_POST(url, data).content

        #Get download link
        dialog.update(100)
        
        sPattern = '''<div id="player_code">.*?<script type='text/javascript'>(eval.+?)</script>'''
        r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)

        if r:
          sJavascript = r.group(1)
          sUnpacked = jsunpack.unpack(sJavascript)
          sUnpacked = sUnpacked.replace("\\","")
                   
        r = re.search("addVariable.+?'file','(.+?)'", sUnpacked)
                
        if r:
            return r.group(1)
        else:
            sPattern  = '<embed id="np_vid"type="video/divx"src="(.+?)'
            sPattern += '"custommode='
            r = re.search(sPattern, sUnpacked)
            if r:
                return r.group(1)
            else:
                addon.log_error('***** 360Gig - Cannot find final link')
                raise Exception('Unable to resolve 360Gig Link')

    except Exception, e:
        addon.log_error('**** 360Gig Error occured: %s' % e)
        raise
    finally:
        dialog.close()


def SHARED2_HANDLER(url):

    html = net.http_GET(url).content

    #Check if a download limit msg is showing
    if re.search('Your free download limit is over.', html):
      wait_time = re.search('<span id="timeToWait">(.+?)</span>', html).group(1)
      Notify('big','2Shared Download Limit Exceeded','You have reached your download limit', '', '', 'You must wait ' + wait_time + ' to try again' )
      return None

    #If no download limit msg lets grab link, must post to it first for download to activate
    else:
      d3fid = re.search('<input type="hidden" name="d3fid" value="(.+?)">', html).group(1)
      d3link = re.search('<input type="hidden" name="d3link" value="(.+?)">', html).group(1)
      data = {'d3fid': d3fid, 'd3link': d3link}
      html = net.http_POST(url, data).content
      return d3link