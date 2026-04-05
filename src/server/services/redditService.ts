import { context, reddit } from '@devvit/web/server';
import type { T3 } from '@devvit/shared-types/tid.js';
import {
  COMMENT_EXCERPT_LENGTH,
  POST_FETCH_LIMIT,
  TOP_COMMENT_LIMIT,
} from '../config/keywords';
import {
  getExcludedCandidateReason,
} from '../config/exclusion';
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
    .filter((post) => {
      const reason = getExcludedCandidateReason(
        { title: post.title, author: post.authorName },
        appUser?.username
      );

      if (reason) {
        console.debug('Skipping excluded candidate during ingest:', reason, post.title, post.authorName);
        return false;
      }

      return true;
    })
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
          author: comment.authorName || '[deleted]',
          body: comment.body ?? '',
          body_excerpt: normalizeExcerpt(comment.body, COMMENT_EXCERPT_LENGTH),
          score: comment.score,
          created_utc: Math.floor(comment.createdAt.getTime() / 1000),
        };
      } catch {
        return {
          comment_id: comment.id,
          author: comment.authorName || '[deleted]',
          body: comment.body ?? '',
          body_excerpt: '',
          score: comment.score,
          created_utc: Math.floor(comment.createdAt.getTime() / 1000),
        };
      }
    })
    .filter((comment) => comment.body_excerpt.length > 0);
};
