import type { CandidateScoreResult, TopComment } from '../../shared/candidate';
import {
  LONG_COMMENT_MIN_LENGTH,
  SHORT_TITLE_MAX_LENGTH,
  VERY_SHORT_BODY_MAX_LENGTH,
  bodyComparisonPatterns,
  bodyUsagePatterns,
  comparisonTitlePatterns,
  deletedRemovedPatterns,
  experienceCommentPatterns,
  lowQualityTitlePatterns,
  memeReactionPatterns,
  negativeOpinionPatterns,
  positiveOpinionPatterns,
  specificQuestionPatterns,
  switchTitlePatterns,
  useCaseTitlePatterns,
  weakTitlePatterns,
  workflowTitlePatterns,
  worthItTitlePatterns,
} from '../config/keywords';

type CandidateScoringInput = {
  createdUtc: number;
  title: string;
  body: string;
  numComments: number;
  topComments: TopComment[];
};

const hasMatch = (value: string, patterns: RegExp[]): boolean =>
  patterns.some((pattern) => pattern.test(value));

const countLongComments = (comments: TopComment[]): number =>
  comments.filter((comment) => comment.body_excerpt.length >= LONG_COMMENT_MIN_LENGTH)
    .length;

const hasSpecificQuestion = (body: string): boolean =>
  body.includes('?') && hasMatch(body, specificQuestionPatterns);

const hasDeletedRemovedContent = (body: string, topComments: TopComment[]): boolean => {
  if (hasMatch(body, deletedRemovedPatterns)) {
    return true;
  }

  return topComments.some((comment) =>
    hasMatch(comment.body_excerpt, deletedRemovedPatterns)
  );
};

const hasMemeReactionContent = (title: string, body: string): boolean => {
  const normalized = `${title} ${body}`.trim();
  if (hasMatch(normalized, memeReactionPatterns)) {
    return true;
  }

  if (body.length === 0 || body.length > VERY_SHORT_BODY_MAX_LENGTH) {
    return false;
  }

  const emojiMatches = body.match(/[\p{Extended_Pictographic}]/gu);
  return (emojiMatches?.length ?? 0) >= 3;
};

const hasDivergingOpinions = (topComments: TopComment[]): boolean => {
  const combined = topComments.map((comment) => comment.body_excerpt);
  const hasPositive = combined.some((body) => hasMatch(body, positiveOpinionPatterns));
  const hasNegative = combined.some((body) => hasMatch(body, negativeOpinionPatterns));
  return hasPositive && hasNegative;
};

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

export const scoreCandidate = (
  input: CandidateScoringInput
): CandidateScoreResult => {
  const reasonTags = new Set<string>();
  let score = 0;

  const normalizedTitle = input.title.replace(/\s+/g, ' ').trim();
  const normalizedBody = input.body.trim();
  const titleLength = normalizedTitle.length;

  const hasWorkflowTitle = hasMatch(normalizedTitle, workflowTitlePatterns);
  const hasComparisonTitle = hasMatch(normalizedTitle, comparisonTitlePatterns);
  const hasWorthItTitle = hasMatch(normalizedTitle, worthItTitlePatterns);
  const hasUseCaseTitle = hasMatch(normalizedTitle, useCaseTitlePatterns);
  const hasSwitchTitle = hasMatch(normalizedTitle, switchTitlePatterns);
  const hasWeakTitle = hasMatch(normalizedTitle, weakTitlePatterns);
  const hasLowQualityTitle = hasMatch(normalizedTitle, lowQualityTitlePatterns);

  if (hasWorkflowTitle) {
    score += 3;
    reasonTags.add('title_workflow_pattern');
  }

  if (hasComparisonTitle) {
    score += 2;
    reasonTags.add('title_comparison_pattern');
  }

  if (hasWorthItTitle) {
    score += 2;
    reasonTags.add('title_worth_it_pattern');
  }

  if (hasUseCaseTitle) {
    score += 2;
    reasonTags.add('title_use_case_pattern');
  }

  if (hasSwitchTitle) {
    score += 2;
    reasonTags.add('title_switch_pattern');
  }

  if (
    hasWeakTitle &&
    !hasWorkflowTitle &&
    !hasComparisonTitle &&
    !hasWorthItTitle &&
    !hasUseCaseTitle &&
    !hasSwitchTitle
  ) {
    score += 1;
    reasonTags.add('title_weak_info_pattern');
  }

  if (titleLength <= SHORT_TITLE_MAX_LENGTH) {
    score -= 1;
    reasonTags.add('short_title');
  }

  if (hasLowQualityTitle) {
    score -= 1;
    reasonTags.add('low_quality_title_pattern');
  }

  if (normalizedBody.length >= 120) {
    score += 1;
    reasonTags.add('body_has_min_context');
  }

  if (hasMatch(normalizedBody, bodyUsagePatterns)) {
    score += 1;
    reasonTags.add('body_has_usage_context');
  }

  if (hasMatch(normalizedBody, bodyComparisonPatterns)) {
    score += 1;
    reasonTags.add('body_has_comparison_context');
  }

  if (hasSpecificQuestion(normalizedBody)) {
    score += 1;
    reasonTags.add('body_has_specific_question');
  }

  if (input.numComments >= 40) {
    score += 4;
    reasonTags.add('comment_volume_40_plus');
  } else if (input.numComments >= 20) {
    score += 3;
    reasonTags.add('comment_volume_20_plus');
  } else if (input.numComments >= 10) {
    score += 2;
    reasonTags.add('comment_volume_10_plus');
  } else if (input.numComments >= 5) {
    score += 1;
    reasonTags.add('comment_volume_5_plus');
  }

  const longCommentCount = countLongComments(input.topComments);
  if (longCommentCount >= 1) {
    score += 1;
    reasonTags.add('has_one_long_comment');
  }

  if (longCommentCount >= 2) {
    score += 1;
    reasonTags.add('has_two_long_comments');
  }

  if (
    input.topComments.some((comment) =>
      hasMatch(comment.body_excerpt, experienceCommentPatterns)
    )
  ) {
    score += 1;
    reasonTags.add('has_experience_comment');
  }

  if (hasDivergingOpinions(input.topComments)) {
    score += 1;
    reasonTags.add('has_diverging_opinions');
  }

  const nowUtc = Math.floor(Date.now() / 1000);
  const ageSeconds = Math.max(0, nowUtc - input.createdUtc);
  const ageDays = ageSeconds / 86400;

  if (ageDays <= 3) {
    score += 3;
    reasonTags.add('recent_3d');
  } else if (ageDays <= 7) {
    score += 2;
    reasonTags.add('recent_7d');
  } else if (ageDays <= 14) {
    score += 1;
    reasonTags.add('recent_14d');
  }

  if (titleLength <= SHORT_TITLE_MAX_LENGTH) {
    score -= 1;
    reasonTags.add('penalty_short_title');
  }

  if (
    normalizedBody.length > 0 &&
    normalizedBody.length <= VERY_SHORT_BODY_MAX_LENGTH
  ) {
    score -= 2;
    reasonTags.add('penalty_too_short_body');
  }

  if (input.numComments < 3) {
    score -= 2;
    reasonTags.add('penalty_low_comment_count');
  }

  if (hasDeletedRemovedContent(normalizedBody, input.topComments)) {
    score -= 3;
    reasonTags.add('penalty_deleted_or_removed');
  }

  if (hasMemeReactionContent(normalizedTitle, normalizedBody)) {
    score -= 2;
    reasonTags.add('penalty_meme_or_reaction');
  }

  return {
    score: clamp(score, -10, 20),
    reason_tags: [...reasonTags],
  };
};
