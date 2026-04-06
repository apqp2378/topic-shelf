from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.url_fetchers.comment_expander import (
    NoOpCommentExpander,
    cap_comments,
    extract_comment_thread_snapshot,
    normalize_comment_node,
    normalize_comment_nodes,
)
from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT


class CommentExpanderTests(unittest.TestCase):
    def test_normalize_comment_node_handles_deleted_author_and_missing_name(self) -> None:
        node = {
            "id": "abc123",
            "author": " ",
            "body": "  helpful body  ",
            "score": "7",
            "created_utc": "1710000001",
        }

        normalized = normalize_comment_node(node)

        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["comment_id"], "t1_abc123")
        self.assertEqual(normalized["author"], "[deleted]")
        self.assertEqual(normalized["body"], "helpful body")
        self.assertEqual(normalized["score"], 7)
        self.assertEqual(normalized["created_utc"], 1710000001)

    def test_cap_comments_uses_shared_limit(self) -> None:
        comments = [{"comment_id": f"t1_{index}"} for index in range(TOP_COMMENT_LIMIT + 2)]

        self.assertEqual(len(cap_comments(comments)), TOP_COMMENT_LIMIT)

    def test_normalize_comment_nodes_caps_and_normalizes(self) -> None:
        nodes = [
            {
                "name": f"t1_comment_{index + 1}",
                "author": "tester",
                "body": f" body {index + 1} ",
                "score": index,
                "created_utc": 1710000000 + index,
            }
            for index in range(TOP_COMMENT_LIMIT + 1)
        ]

        normalized = normalize_comment_nodes(nodes)

        self.assertEqual(len(normalized), TOP_COMMENT_LIMIT)
        self.assertEqual(normalized[0]["comment_id"], "t1_comment_1")
        self.assertEqual(normalized[0]["body"], "body 1")

    def test_noop_expander_returns_capped_normalized_comments(self) -> None:
        expander = NoOpCommentExpander()
        comments = [
            {
                "comment_id": f"t1_{index + 1}",
                "author": "tester",
                "body": "body",
                "score": index,
                "created_utc": 1710000000 + index,
            }
            for index in range(TOP_COMMENT_LIMIT + 3)
        ]

        expanded = expander.expand(comments)

        self.assertEqual(len(expanded), TOP_COMMENT_LIMIT)
        self.assertEqual(expanded[0]["comment_id"], "t1_1")

    def test_comment_thread_snapshot_separates_initial_and_expandable_ids(self) -> None:
        children = [
            {
                "kind": "t1",
                "data": {
                    "id": "comment_1",
                    "name": "t1_comment_1",
                    "author": "tester",
                    "body": "body",
                    "score": 1,
                    "created_utc": 1710000000,
                },
            },
            {
                "kind": "more",
                "data": {
                    "children": ["t1_more_1", "t1_more_2"],
                },
            },
        ]

        snapshot = extract_comment_thread_snapshot(children)

        self.assertEqual(snapshot.comment_fetch_count, 1)
        self.assertEqual(len(snapshot.initial_comment_nodes), 1)
        self.assertEqual(snapshot.expandable_comment_ids, ["t1_more_1", "t1_more_2"])
        self.assertEqual(snapshot.comment_fetch_depth, 0)


if __name__ == "__main__":
    unittest.main()
