# -*- coding: utf-8 -*-
#
# Blackbirdpy - a Python implementation of Blackbird Pie, the tool
# @robinsloan uses to generate embedded HTML tweets for blog posts.
#
# See: http://media.twitter.com/blackbird-pie
#
# This Python version was written by Jeff Miller, http://twitter.com/jeffmiller
#
# Requires Python 2.6.
#
# Usage:
#
# - To generate embedded HTML for a tweet from inside a Python program:
#
#   import blackbirdpy
#   embed_html = blackbirdpy.embed_tweet_html(tweet_url)
#
# - To generate embedded HTML for a tweet from the command line:
#
#   $ python blackbirdpy.py <tweeturl>
#     e.g.
#   $ python blackbirdpy.py http://twitter.com/punchfork/status/16342628623
#
# - To run unit tests from the command line:
#
#   $ python blackbirdpy.py --unittest

import datetime
import email.utils
import json
import optparse
import re
import sys
import unittest
import urllib2


TWEET_EMBED_HTML = u'''<!-- {tweetURL} -->
<style type='text/css'>.bbpBox{id} {{{bbpBoxCss}background:url({profileBackgroundImage}) #{profileBackgroundColor};padding:20px;}} p.bbpTweet{{background:#fff;padding:10px 12px 10px 12px;margin:0;min-height:48px;color:#000;font-size:18px !important;line-height:22px;-moz-border-radius:5px;-webkit-border-radius:5px}} p.bbpTweet span.metadata{{display:block;width:100%;clear:both;margin-top:8px;padding-top:12px;height:40px;border-top:1px solid #fff;border-top:1px solid #e6e6e6}} p.bbpTweet span.metadata span.author{{line-height:19px}} p.bbpTweet span.metadata span.author img{{float:left;margin:0 7px 0 0px;width:38px;height:38px}} p.bbpTweet span.timestamp{{font-size:12px;display:block}}</style>
<div class='bbpBox{id}'><p class='bbpTweet'>{tweetText}<span class='timestamp'><a title='{timeStamp}' href='{tweetURL}'>{easyTimeStamp}</a> via {source}</span><span class='metadata'><span class='author'><a href='http://twitter.com/{screenName}'><img src='{profilePic}' /></a><strong><a href='http://twitter.com/{screenName}'>{realName}</a></strong><br/>{screenName}</span></span></p></div>
<!-- end of tweet -->'''


def wrap_user_mention_with_link(text):
    """Replace @user with <a href="http://twitter.com/user">@user</a>"""
    return re.sub(r'(^|[^\w])@(\w+)\b', r'\1<a href="http://twitter.com/\2">@\2</a>', text)


def wrap_hashtag_with_link(text):
    """Replace #hashtag with <a href="http://twitter.com/search?q=hashtag">#hashtag</a>"""
    return re.sub(r'(^|[^\w])#(\w+)\b', r'\1<a href="http://twitter.com/search?q=\2">#\2</a>', text)


def wrap_http_with_link(text):
    """Replace http://foo with <a href="http://foo">http://foo</a>"""
    return re.sub(r'(^|[^\w])(http://[^\s]+)', r'\1<a href="\2">\2</a>', text)


def timestamp_string_to_datetime(text):
    """Convert a string timestamp of the form 'Wed Jun 09 18:31:55 +0000 2010'
    into a Python datetime object."""
    tm_array = email.utils.parsedate_tz(text)
    return datetime.datetime(*tm_array[:6]) - datetime.timedelta(seconds=tm_array[-1])


def easy_to_read_timestamp_string(dt):
    """Convert a Python datetime object into an easy-to-read timestamp
    string, like '1:33 PM Wed Jun 16, 2010'."""
    return re.sub(r'(^| +)0', r'\1', dt.strftime('%I:%M %p %a %b %d, %Y'))


def tweet_id_from_tweet_url(tweet_url):
    """Extract and return the numeric tweet ID from a full tweet URL."""
    match = re.match(r'^http://twitter\.com/\w+/status(?:es)?/(\d+)$', tweet_url)
    try:
        return match.group(1)
    except AttributeError:
        raise ValueError('Invalid tweet URL: {0}'.format(tweet_url))


def embed_tweet_html(tweet_url, extra_css=None):
    """Generate embedded HTML for a tweet, given its Twitter URL.  The
    result is formatted in the style of Robin Sloan's Blackbird Pie.
    See: http://media.twitter.com/blackbird-pie

    The optional extra_css argument is a dictionary of CSS class names
    to CSS style text.  If provided, the extra style text will be
    included in the embedded HTML CSS.  Currently only the bbpBox
    class name is used by this feature.
    """
    tweet_id = tweet_id_from_tweet_url(tweet_url)
    api_url = 'http://api.twitter.com/1/statuses/show.json?id=' + tweet_id
    api_handle = urllib2.urlopen(api_url)
    api_data = api_handle.read()
    api_handle.close()
    tweet_json = json.loads(api_data)

    tweet_text = wrap_user_mention_with_link(
        wrap_hashtag_with_link(
            wrap_http_with_link(
                tweet_json['text'].replace('\n', ' ')
                )
            )
        )

    tweet_created_datetime = timestamp_string_to_datetime(tweet_json["created_at"])
    tweet_local_datetime = tweet_created_datetime + (datetime.datetime.now() - datetime.datetime.utcnow())
    tweet_easy_timestamp = easy_to_read_timestamp_string(tweet_local_datetime)

    if extra_css is None:
        extra_css = {}

    html = TWEET_EMBED_HTML.format(
        id=tweet_id,
        tweetURL=tweet_url,
        screenName=tweet_json['user']['screen_name'],
        realName=tweet_json['user']['name'],
        tweetText=tweet_text,
        source=tweet_json['source'],
        profilePic=tweet_json['user']['profile_image_url'],
        profileBackgroundColor=tweet_json['user']['profile_background_color'],
        profileBackgroundImage=tweet_json['user']['profile_background_image_url'],
        profileTextColor=tweet_json['user']['profile_text_color'],
        profileLinkColor=tweet_json['user']['profile_link_color'],
        timeStamp=tweet_json['created_at'],
        easyTimeStamp=tweet_easy_timestamp,
        utcOffset=tweet_json['user']['utc_offset'],
        bbpBoxCss=extra_css.get('bbpBox', ''),
    )
    return html


class TestWrapUserMentionWithLink(unittest.TestCase):
    def test_basic(self):
        test_cases = [
            ('@user', '<a href="http://twitter.com/user">@user</a>'),
            ('Hey @user: hey', 'Hey <a href="http://twitter.com/user">@user</a>: hey'),
            ('@foo and @bar', '<a href="http://twitter.com/foo">@foo</a> and <a href="http://twitter.com/bar">@bar</a>'),
            ('Nothing to wrap', 'Nothing to wrap'),
            ('', ''),
            ]
        for input, expected_output in test_cases:
            self.assertEqual(wrap_user_mention_with_link(input), expected_output)


class TestWrapHashtagWithLink(unittest.TestCase):
    def test_basic(self):
        test_cases = [
            ('#foo', '<a href="http://twitter.com/search?q=foo">#foo</a>'),
            ('Total #fail!', 'Total <a href="http://twitter.com/search?q=fail">#fail</a>!'),
            ('#qiz #quz', '<a href="http://twitter.com/search?q=qiz">#qiz</a> <a href="http://twitter.com/search?q=quz">#quz</a>'),
            ('Nothing to wrap', 'Nothing to wrap'),
            ('', ''),
            ]
        for input, expected_output in test_cases:
            self.assertEqual(wrap_hashtag_with_link(input), expected_output)


class TestWrapHttpWithLink(unittest.TestCase):
    def test_basic(self):
        test_cases = [
            ('http://foo', '<a href="http://foo">http://foo</a>'),
            ('See http://media.twitter.com/blackbird-pie/ for more info',
             'See <a href="http://media.twitter.com/blackbird-pie/">http://media.twitter.com/blackbird-pie/</a> for more info'),
            ('Nothing to wrap', 'Nothing to wrap'),
            ('', ''),
            ]
        for input, expected_output in test_cases:
            self.assertEqual(wrap_http_with_link(input), expected_output)


class TestTimestampStringToDatetime(unittest.TestCase):
    def test_basic(self):
        test_cases = [
            ('Wed Jun 09 18:31:55 +0000 2010', datetime.datetime(2010, 6, 9, 18, 31, 55, 0)),
            ('Mon Jan 11 5:01:00 +0200 1998', datetime.datetime(1998, 1, 11, 3, 1, 00, 0)),
            ('Tue Nov 23 23:01:00 -0500 2004', datetime.datetime(2004, 11, 24, 4, 1, 00, 0)),
            ]
        for input, expected_output in test_cases:
            self.assertEqual(timestamp_string_to_datetime(input), expected_output)


class TestEasyToReadTimestampString(unittest.TestCase):
    def test_basic(self):
        test_cases = [
            (datetime.datetime(2010, 6, 9, 18, 31, 55, 0), '6:31 PM Wed Jun 9, 2010'),
            (datetime.datetime(1998, 1, 11, 3, 1, 00, 0), '3:01 AM Sun Jan 11, 1998'),
            (datetime.datetime(2004, 11, 23, 23, 1, 00, 0), '11:01 PM Tue Nov 23, 2004'),
            ]
        for input, expected_output in test_cases:
            self.assertEqual(easy_to_read_timestamp_string(input), expected_output)


class TestTweetIdFromTweetUrl(unittest.TestCase):
    def test_basic(self):
        test_cases = [
            ('http://twitter.com/foo/status/1234567890', '1234567890'),
            ('http://twitter.com/bar99/statuses/555555', '555555'),
            ]
        for input, expected_output in test_cases:
            self.assertEqual(tweet_id_from_tweet_url(input), expected_output)

    def test_failure(self):
        test_cases = [
            'not a url',
            'http://twitter.com/status/2345678',
            'http://twitter.com/foo/status/',
            'http://twitter.com/foo/status/ ',
            ]
        for input in test_cases:
            self.assertRaises(ValueError, tweet_id_from_tweet_url, input)


if __name__ == '__main__':
    option_parser = optparse.OptionParser(usage='%prog [options] tweeturl')
    option_parser.add_option('--unittest', dest='unittest', action='store_true', default=False,
                             help='Run unit tests and exit')
    options, args = option_parser.parse_args()

    if options.unittest:
        unittest.main(argv=[sys.argv[0]])
        sys.exit(0)

    if len(args) != 1:
        option_parser.print_help()
        sys.exit(1)

    print embed_tweet_html(args[0])
