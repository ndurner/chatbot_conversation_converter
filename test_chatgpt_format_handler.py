import unittest

from chatbot_convert import convert_format, detect_format
from chatgpt_format_handler import ChatGPTFormatHandler


class ChatGPTHTMLTests(unittest.TestCase):
    def test_current_html_preserves_order_roles_and_formatting(self):
        html = '''<html><body>
          <nav>Sidebar conversation</nav>
          <div data-content-search-unit-key="turn:0:user">
            <div data-user-message-bubble="true"><div>Hello\n\nNext line</div></div>
            <button>Edit message</button>
          </div>
          <div data-chatgpt-selection-message-id="answer">
            <div data-markdown-text-style="assistant-message">
              <h2>Answer</h2><p>A <strong>bold</strong> reply.</p>
              <pre><div>python</div><code>print("hello")</code></pre>
            </div><button>Copy response</button>
          </div>
          <div data-user-message-bubble="true">
            <div data-markdown-text-tone="user-message">
              <p>Follow <em>up</em>.</p><p>Another paragraph.</p>
            </div>
          </div>
          <div data-markdown-text-style="assistant-message">
            <p>Final <span data-d-default-strong>answer</span> with
              <span data-d-font-style="italic">emphasis</span>.</p>
            <div data-d-component="divider"></div>
            <table><tr><th>Header</th></tr><tr><td>Value</td></tr></table>
            <div hidden>Hidden controls</div><button>Copy</button>
          </div>
          <div contenteditable="true">Composer draft</div>
        </body></html>'''
        self.assertIsInstance(detect_format(html), ChatGPTFormatHandler)
        messages = convert_format(html, "workbench")["messages"]
        self.assertEqual([m["role"] for m in messages],
                         ["user", "assistant", "user", "assistant"])
        self.assertEqual(messages[0]["content"], "Hello\n\nNext line")
        self.assertIn('```python\nprint("hello")\n```', messages[1]["content"])
        self.assertIn("## Answer\n\nA **bold** reply.", messages[1]["content"])
        self.assertEqual(messages[2]["content"], "Follow *up*.\n\nAnother paragraph.")
        self.assertIn("**answer**", messages[3]["content"])
        self.assertIn("*emphasis*", messages[3]["content"])
        self.assertIn("\n---\n", messages[3]["content"])
        self.assertIn("| Header |\n| --- |\n| Value |", messages[3]["content"])
        markdown = convert_format(html, "markdown")
        self.assertEqual(markdown.count("::: user\n"), 2)
        self.assertEqual(markdown.count("::: assistant\n"), 2)
        for ui_text in ("Sidebar conversation", "Edit message", "Copy response",
                        "Hidden controls", "Composer draft"):
            self.assertNotIn(ui_text, markdown)

    def test_empty_message_roots_are_ignored(self):
        html = '''<div data-user-message-bubble="true">Question</div>
          <div data-markdown-text-style="assistant-message"><p></p></div>
          <div data-markdown-text-style="assistant-message"><p>Response</p></div>'''
        self.assertEqual(convert_format(html, "workbench"), {"messages": [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Response"},
        ]})

    def test_non_conversation_html_and_json_are_not_detected_as_chatgpt(self):
        for data in (None, {"messages": []}, "<p>ordinary page</p>",
                     '<script>"data-user-message-bubble"</script>'):
            with self.subTest(data=data):
                self.assertFalse(ChatGPTFormatHandler.can_handle(data))


if __name__ == "__main__":
    unittest.main()
