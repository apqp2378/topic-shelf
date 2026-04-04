export const LONG_COMMENT_MIN_LENGTH = 180;
export const VERY_SHORT_BODY_MAX_LENGTH = 40;
export const SHORT_TITLE_MAX_LENGTH = 8;
export const TOP_COMMENT_LIMIT = 5;
export const POST_FETCH_LIMIT = 30;
export const BODY_EXCERPT_LENGTH = 300;
export const COMMENT_EXCERPT_LENGTH = 220;

export const workflowTitlePatterns = [
  /after using/i,
  /my observations/i,
  /workflow/i,
  /what'?s working/i,
  /trying to build/i,
  /real-world advice/i,
  /daily driver/i,
  /besides coding/i,
];

export const comparisonTitlePatterns = [/ vs /i, /better than/i];

export const worthItTitlePatterns = [/worth it/i, /should i/i, /is .* worth it/i];

export const useCaseTitlePatterns = [
  /how do you use/i,
  /what do you use it for/i,
  /how is everyone using/i,
  /favorite ways to use/i,
];

export const switchTitlePatterns = [/switch/i, /switched/i];

export const weakTitlePatterns = [/review/i, /guide/i, /tips/i, /tutorial/i, /best/i, /thoughts/i];

export const lowQualityTitlePatterns = [/help/i, /question/i, /thoughts\?/i, /wow/i];

export const bodyUsagePatterns = [
  /i use/i,
  /i used/i,
  /i switched/i,
  /for work/i,
  /for my job/i,
  /for research/i,
  /for coding/i,
  /for writing/i,
  /i am trying to/i,
  /my workflow/i,
  /my use case/i,
  /my problem is/i,
];

export const bodyComparisonPatterns = [
  /compared to/i,
  /versus/i,
  /\bvs\b/i,
  /instead of/i,
  /better than/i,
  /worse than/i,
];

export const specificQuestionPatterns = [
  /which should/i,
  /what should/i,
  /is it better/i,
  /for my use case/i,
  /for work/i,
  /for coding/i,
  /for research/i,
  /on a budget/i,
  /if i already use/i,
  /compared to/i,
];

export const experienceCommentPatterns = [
  /i use/i,
  /i used/i,
  /i switched/i,
  /in my case/i,
  /for my workflow/i,
  /for work/i,
  /for coding/i,
  /for research/i,
  /i prefer/i,
];

export const positiveOpinionPatterns = [/better/i, /worth it/i, /useful/i, /good/i, /prefer/i];

export const negativeOpinionPatterns = [
  /not worth/i,
  /worse/i,
  /bad/i,
  /overpriced/i,
  /wouldn'?t/i,
];

export const memeReactionPatterns = [
  /lol/i,
  /lmao/i,
  /meme/i,
  /shitpost/i,
  /just for fun/i,
  /look at this/i,
];

export const deletedRemovedPatterns = [/\[deleted\]/i, /\[removed\]/i];
