import unittest
from unittest.mock import Mock, patch
import io
import json

from compatibility.voyage_http import VoyageContractError, VoyageHTTPProbe, ordered_items, post_json


def context_response(*, text=True, dimension=256):
    row = {"index": 0, "embedding": [0.5] * dimension}
    if text:
        row["text"] = "Synthetic chunk"
    return {"model": "voyage-context-4", "data": [{"index": 0, "data": [row]}]}


class VoyageContractTests(unittest.TestCase):
    def test_atlas_key_uses_explicit_atlas_endpoint(self):
        opener = Mock()
        opener.open.return_value = io.BytesIO(json.dumps({"data": []}).encode())
        with patch("compatibility.voyage_http.build_opener", return_value=opener):
            post_json("rerank", {}, "dummy", base_url="https://ai.mongodb.com/v1")
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://ai.mongodb.com/v1/rerank")

    def test_untrusted_endpoint_is_rejected_before_sending_key(self):
        with patch("compatibility.voyage_http.build_opener") as opener:
            with self.assertRaises(VoyageContractError):
                post_json("rerank", {}, "dummy", base_url="https://example.com/v1")
            opener.assert_not_called()

    def test_document_request_uses_server_chunking_and_preserves_text(self):
        transport = Mock(return_value=context_response())
        result = VoyageHTTPProbe("dummy", transport).contextual(["Synthetic document"], documents=True)
        endpoint, payload, _ = transport.call_args.args
        self.assertEqual(endpoint, "contextualizedembeddings")
        self.assertTrue(payload["enable_auto_chunking"])
        self.assertEqual(payload["input_type"], "document")
        self.assertEqual(result["data"][0]["data"][0]["text"], "Synthetic chunk")

    def test_query_does_not_request_auto_chunking(self):
        transport = Mock(return_value=context_response(text=False))
        VoyageHTTPProbe("dummy", transport).contextual(["Question"], documents=False)
        self.assertNotIn("enable_auto_chunking", transport.call_args.args[1])
        self.assertEqual(transport.call_args.args[1]["input_type"], "query")

    def test_provider_dimension_mismatch_is_rejected(self):
        transport = Mock(return_value=context_response(dimension=512))
        with self.assertRaises(VoyageContractError):
            VoyageHTTPProbe("dummy", transport).contextual(["Question"], documents=False)

    def test_document_without_chunk_text_is_rejected(self):
        with self.assertRaises(VoyageContractError):
            VoyageHTTPProbe("dummy", Mock(return_value=context_response(text=False))).contextual(["Doc"], documents=True)

    def test_duplicate_indices_cannot_silently_map_to_wrong_source(self):
        with self.assertRaises(VoyageContractError):
            ordered_items([{"index": 0}, {"index": 0}])
        self.assertEqual(ordered_items([{"index": 1}, {"index": 0}])[0]["index"], 0)

    def test_invalid_dimensions_fail_before_network(self):
        transport = Mock()
        with self.assertRaises(VoyageContractError):
            VoyageHTTPProbe("dummy", transport).contextual(["Doc"], documents=True, dimension=12)
        transport.assert_not_called()

    def test_rerank_preserves_document_indices(self):
        transport = Mock(return_value={"data": [{"index": 1, "relevance_score": 0.8}, {"index": 0, "relevance_score": 0.2}]})
        result = VoyageHTTPProbe("dummy", transport).rerank("q", ["a", "b"])
        self.assertEqual(result["data"][0]["index"], 1)
        self.assertEqual(transport.call_args.args[1]["model"], "rerank-3")
        self.assertFalse(transport.call_args.args[1]["truncation"])

    def test_out_of_range_reranking_index_is_rejected(self):
        transport = Mock(return_value={"data": [{"index": 8, "relevance_score": 0.8}]})
        with self.assertRaises(VoyageContractError):
            VoyageHTTPProbe("dummy", transport).rerank("q", ["a"], 1)

    def test_nan_vectors_are_rejected(self):
        response = context_response()
        response["data"][0]["data"][0]["embedding"][0] = float("nan")
        with self.assertRaises(VoyageContractError):
            VoyageHTTPProbe("dummy", Mock(return_value=response)).contextual(["Doc"], documents=True)


if __name__ == "__main__":
    unittest.main()
