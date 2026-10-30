from gitscribe.mask import mask

SAMPLE = """+OPENAI_API_KEY=abcd1234efgh
+export GITHUB_TOKEN="ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
+    api_key = "plainsecret99"
+headers = {"Authorization": "Bearer abcdefghijklmnopqrstu"}
+client = OpenAI(key="sk-proj-ABCDEFGHIJKLMNOP1234")
+author = "Hong <hong.gildong@example.co.kr>"
+phone: 010-1234-5678
+password = request.form["password"]
+token = get_token()
"""


def test_mask():
    masked, count = mask(SAMPLE)
    for secret in [
        "abcd1234efgh",
        "ghp_",
        "plainsecret99",
        "abcdefghijklmnopqrstu",
        "sk-proj",
        "hong.gildong",
        "010-1234",
    ]:
        assert secret not in masked, secret
    # 비밀값이 아닌 코드는 그대로 둔다.
    assert (
        'password = request.form["password"]' in masked
        and "token = get_token()" in masked
    )
    assert count == 7, (count, masked)


if __name__ == "__main__":
    test_mask()
    print("ok")
