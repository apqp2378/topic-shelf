import { context, reddit } from '@devvit/web/server';
import type { T3 } from '@devvit/shared-types/tid.js';
import {
  COMMENT_EXCERPT_LENGTH,
  POST_FETCH_LIMIT,
  TOP_COMMENT_LIMIT,
} from '../config/keywords';
import type { TopComment } from '../../shared/candidate';

export type RedditPostRecord = {
  post_id: T3;
  permalink: string;
  title: string;
  author: string;
  subreddit: string;
  created_utc: number;
  upvotes: number;
  num_comments: number;
  body: string;
};

const normalizeExcerpt = (value: string, maxLength: number): string =>
  value.replace(/\s+/g, ' ').trim().slice(0, maxLength);

const normalizeTitle = (value: string): string => value.replace(/\s+/g, ' ').trim().toLowerCase();

const shouldExcludePost = (postTitle: string, authorName: string, appUserName: string | undefined): boolean => {
  const normalizedTitle = normalizeTitle(postTitle);
  const normalizedAuthor = authorName.trim().toLowerCase();
  const normalizedAppUser = appUserName?.trim().toLowerCase() ?? '';
  const reason =
    normalizedTitle === 'topic-shelf'
      ? 'exact_wrapper_title'
      : normalizedAuthor === 'topic-shelf' || normalizedAuthor === normalizedAppUser
        ? 'exact_wrapper_author'
        : null;

  if (reason) {
    console.debug('Skipping excluded candidate during ingest:', reason, postTitle, authorName);
    return true;
  }

  return false;
};

export const resolveTargetSubreddit = async (): Promise<string> => {
  return context.subredditName;
};

export const fetchRecentPosts = async (
  subredditName: string
): Promise<RedditPostRecord[]> => {
  const appUser = await reddit.getAppUser();
  const posts = await reddit
    .getNewPosts({
      subredditName,
      limit: POST_FETCH_LIMIT,
      pageSize: POST_FETCH_LIMIT,
    })
    .all();

  return posts
    .filter((post) => !shouldExcludePost(post.title, post.authorName, appUser?.username))
    .map((post) => ({
      post_id: post.id,
      permalink: post.permalink,
      title: post.title,
      author: post.authorName,
      subreddit: post.subredditName,
      created_utc: Math.floor(post.createdAt.getTime() / 1000),
      upvotes: post.score,
      num_comments: post.numberOfComments,
      body: post.body ?? '',
    }));
};

export const fetchTopComments = async (postId: T3): Promise<TopComment[]> => {
  const comments = await reddit
    .getComments({
      postId,
      limit: TOP_COMMENT_LIMIT,
      pageSize: TOP_COMMENT_LIMIT,
      sort: 'top',
    })
    .all();

  return comments
    .slice(0, TOP_COMMENT_LIMIT)
    .map((comment) => {
      try {
        return {
          comment_id: comment.id,
          body_excerpt: normalizeExcerpt(comment.body, COMMENT_EXCERPT_LENGTH),
          score: comment.score,
        };
      } catch {
        return {
          comment_id: comment.id,
          body_excerpt: '',
          score: comment.score,
        };
      }
    })
    .filter((comment) => comment.body_excerpt.length > 0);
};
