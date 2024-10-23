import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime
import re
import pandas as pd

# YouTube API configuration
YOUTUBE_API_KEY = "YOUR_API_KEY"  # Replace with your YouTube Data API key


def extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu.be\/)([\w-]+)',  # Standard and shortened URLs
        r'(?:youtube\.com\/shorts\/)([\w-]+)',  # Shorts URLs
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_comments(video_id, max_results=100):
    """Fetch comments for a YouTube video using the YouTube Data API."""
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

        # Get video details first
        video_response = youtube.videos().list(
            part='snippet,statistics',
            id=video_id
        ).execute()

        if not video_response['items']:
            return None, "Video not found"

        video_title = video_response['items'][0]['snippet']['title']
        video_stats = video_response['items'][0]['statistics']

        # Get comments
        comments = []
        results = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            textFormat='plainText',
            maxResults=max_results
        ).execute()

        while results:
            for item in results['items']:
                comment = item['snippet']['topLevelComment']['snippet']

                # Format the timestamp
                published_at = datetime.strptime(
                    comment['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'
                )

                comments.append({
                    'author': comment['authorDisplayName'],
                    'text': comment['textDisplay'],
                    'likes': comment['likeCount'],
                    'published_at': published_at,
                    'reply_count': item['snippet']['totalReplyCount']
                })

            # Check if there are more comments
            if 'nextPageToken' in results and len(comments) < max_results:
                results = youtube.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    textFormat='plainText',
                    maxResults=max_results,
                    pageToken=results['nextPageToken']
                ).execute()
            else:
                break

        return {
            'video_title': video_title,
            'stats': video_stats,
            'comments': comments
        }, None

    except Exception as e:
        return None, str(e)


def main():
    st.title("YouTube Comments Viewer")
    st.write("Enter a YouTube video URL to view its comments")

    # Sidebar controls
    with st.sidebar:
        st.header("Settings")
        max_comments = st.slider("Maximum comments to fetch", 10, 500, 100)

        st.header("Export Options")
        export_format = st.selectbox(
            "Export format",
            ["CSV", "Excel"]
        )

    # Main interface
    url = st.text_input(
        "Enter YouTube Video URL",
        placeholder="https://youtube.com/watch?v=..."
    )

    if st.button("Fetch Comments"):
        if url:
            video_id = extract_video_id(url)

            if video_id:
                with st.spinner("Fetching comments..."):
                    result, error = get_comments(video_id, max_comments)

                    if error:
                        st.error(f"Error: {error}")
                    else:
                        # Display video information
                        st.header(result['video_title'])

                        # Video statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Views", result['stats'].get('viewCount', 'N/A'))
                        with col2:
                            st.metric("Likes", result['stats'].get('likeCount', 'N/A'))
                        with col3:
                            st.metric("Comments", result['stats'].get('commentCount', 'N/A'))

                        st.divider()

                        # Create DataFrame for export
                        df = pd.DataFrame(result['comments'])

                        # Export buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if export_format == "CSV":
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    "Download Comments (CSV)",
                                    csv,
                                    "youtube_comments.csv",
                                    "text/csv",
                                    key='download-csv'
                                )
                            else:
                                excel_buffer = pd.ExcelWriter('youtube_comments.xlsx', engine='xlsxwriter')
                                df.to_excel(excel_buffer, index=False)
                                st.download_button(
                                    "Download Comments (Excel)",
                                    excel_buffer,
                                    "youtube_comments.xlsx",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key='download-excel'
                                )

                        # Display comments
                        st.subheader(f"Comments ({len(result['comments'])})")
                        for comment in result['comments']:
                            with st.container():
                                st.markdown(f"**{comment['author']}**")
                                st.write(comment['text'])
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.caption(f"Posted: {comment['published_at'].strftime('%Y-%m-%d %H:%M')}")
                                with col2:
                                    st.caption(f"❤️ {comment['likes']}")
                                with col3:
                                    st.caption(f"💬 {comment['reply_count']}")
                                st.divider()
            else:
                st.error("Invalid YouTube URL. Please check the URL and try again.")


if __name__ == "__main__":
    main()