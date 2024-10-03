from django.shortcuts import render, redirect
from django.views.generic import View
from django.views.generic.base import View
from googleapiclient.discovery import build
from datetime import datetime, timedelta, date
from django.conf import settings
from .forms import KeywordForm
import pandas as pd
from django.http.response import HttpResponse

class CallbackView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')


YOUTUBE_API = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)

def search_video(keyword, items_count, order, search_start, search_end):
    result = YOUTUBE_API.search().list(
        part='snippet',
        q=keyword,
        maxResults=items_count,
        order=order,
        publishedAfter=search_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
        publishedBefore=search_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
        type='video',
        regionCode='JP'
    ).execute()

    search_list = []
    for item in result['items']:
        published_at = datetime.strptime(item['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
        search_list.append([
            item['id']['videoId'],
            item['snippet']['channelId'],
            published_at,
            item['snippet']['title'],
            item['snippet']['channelTitle'],
        ])
    return search_list

def get_channel(videoid_list):
    channel_list = []
    for videoid, channelid in videoid_list.items():
        result = YOUTUBE_API.channels().list(
            part='snippet',
            id=channelid,
        ).execute()

        for item in result['items']:
            channel_list.append([
                videoid,
                item['snippet']['thumbnails']['default']['url']
            ])
    return channel_list

def get_video(videoid_list):
    count_list = []
    for videoid, channelid in videoid_list.items():
        result = YOUTUBE_API.videos().list(
            part='statistics',
            maxResults=50,
            id=videoid
        ).execute()

        for item in result['items']:
            try:
                likeCount = item['statistics']['likeCount']
                favoriteCount = item['statistics']['favoriteCount']
                commentCount = item['statistics']['commentCount']
            except KeyError:
                likeCount = '-'
                favoriteCount = '-'
                commentCount = '-'

            count_list.append([
                item['id'],
                item['statistics']['viewCount'],
                likeCount,
                favoriteCount,
                commentCount
            ])
    return count_list

def make_df(search_list, channel_list, count_list, viewcount):
    youtube_data = pd.DataFrame(search_list, columns=[
        'videoid',
        'channelId',
        'publishtime',
        'title',
        'channeltitle',
    ])

    youtube_data.drop_duplicates(subset='videoid', inplace=True)

    youtube_data['url'] = 'https://www.youtube.com/embed/' + youtube_data['videoid']

    df_channel = pd.DataFrame(channel_list, columns=[
        'videoid',
        'profileImg'
    ])

    df_viewcount = pd.DataFrame(count_list, columns=[
        'videoid',
        'viewcount',
        'likeCount',
        'favoriteCount',
        'commentCount'
    ])

    youtube_data = pd.merge(df_channel, youtube_data, on='videoid', how='left')
    youtube_data = pd.merge(df_viewcount, youtube_data, on='videoid', how='left')

    youtube_data['viewcount'] = youtube_data['viewcount'].astype(int)

    youtube_data = youtube_data.query('viewcount>=' + str(viewcount))

    youtube_data = youtube_data[[
        'publishtime',
        'title',
        'channeltitle',
        'url',
        'profileImg',
        'viewcount',
        'likeCount',
        'favoriteCount',
        'commentCount',
    ]]

    youtube_data['viewcount'] = youtube_data['viewcount'].astype(str)

    return youtube_data

class IndexView(View):
    def get(self, request, *args, **kwargs):
        form = KeywordForm(
            request.POST or None,
            initial={
                'items_count': 12,
                'viewcount': 1000,
                'order': 'viewCount',
                'search_start': datetime.today() - timedelta(days=30),
                'search_end': datetime.today(),
            }
        )

        return render(request, 'app/index.html', {
            'form': form
        })

    def post(self, request, *args, **kwargs):
        form = KeywordForm(request.POST or None)

        if form.is_valid():
            keyword = form.cleaned_data['keyword']
            items_count = form.cleaned_data['items_count']
            viewcount = form.cleaned_data['viewcount']
            order = form.cleaned_data['order']
            search_start = form.cleaned_data['search_start']
            search_end = form.cleaned_data['search_end']

            search_list = search_video(keyword, items_count, order, search_start, search_end)

            videoid_list = {}
            for item in search_list:
                videoid_list[item[0]] = item[1]

            channel_list = get_channel(videoid_list)

            count_list = get_video(videoid_list)

            youtube_data = make_df(search_list, channel_list, count_list, viewcount)

            return render(request, 'app/keyword.html', {
                'youtube_data': youtube_data,
                'keyword': keyword
            })
        else:
            return redirect('index')