import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from threads_automation.formats import (FormatValidationError, validate_format_master,
                                         validate_quiz_schedule, validate_schedule_manifests,
                                         validate_threads_reply)


def common(fmt):
    return {"content_id":"ENG-900001","format":fmt,"difficulty":"L2","learning_point":"point","question":"Test ___ now.","correct_answer":"right","publish_at":"2026-08-24T07:00:00+09:00","english_correctness":True,"unique_answer":True}


class ThreadsProductionFormatTests(unittest.TestCase):
    def test_text_and_visual_reply_contracts(self):
        for fmt in ("text","visual"):
            x=common(fmt); x.update(choices=["wrong","right"],explanation="短い説明です。",
                completed_sentence="Test right now.",japanese_translation="短い訳です。",
                instagram_caption="caption",threads_parent_text="hook",
                threads_answer_text="✅ 正解は B. right\n\n短い説明です。",
                threads_reply="✅ 正解は B. right\n\n短い説明です。",visual_required=fmt=="visual",
                question_guide_ja="入るのはどっち？",threads_reply_explanation="短い説明です。")
            if fmt=="visual": x.update(question_guide_ja=None,visual_semantic_consistency=True,
                visual_answer_uniqueness=True,visual_only_solvable=False,visual_semantics={
                "subject_gender":"verified","subject_count":"verified","action":"verified",
                "direction":"verified","object":"verified","state":"verified","location":"verified",
                "completed_sentence":"Test right now."})
            validate_format_master(x); validate_threads_reply(x,x["threads_reply"])
            with self.assertRaises(FormatValidationError): validate_threads_reply(x,"✅ 正解は A. right\n\n短い説明です。")

    def test_text_visual_answer_first_and_hint_first_contracts(self):
        base=common("visual"); base.update(choices=["wrong","right"],explanation="短い説明です。",
            completed_sentence="Test right now.",japanese_translation="短い訳です。",
            instagram_caption="caption",threads_parent_text="hook",visual_required=True,
            threads_reply_explanation="短い説明です。",visual_semantic_consistency=True,
            visual_answer_uniqueness=True,visual_only_solvable=False,visual_semantics={
            "subject_gender":"verified","subject_count":"verified","action":"verified",
            "direction":"verified","object":"verified","state":"verified","location":"verified",
            "completed_sentence":"Test right now."})
        answer_first="💡 正解は B. right\n\n短い説明です。"
        base.update(threads_answer_text=answer_first,threads_reply=answer_first)
        validate_format_master(base); validate_threads_reply(base,answer_first)

        for content_id, hint in (("ENG-000041", "女性が手を伸ばしている物に注目。"),
                                 ("ENG-000046", "男性の手の先を見てみよう。")):
            item=dict(base); item.update(content_id=content_id,hint=hint)
            reply=f"💡 {hint}\n\n✅ 正解は B. right\n\n短い説明です。"
            item.update(threads_answer_text=reply,threads_reply=reply)
            validate_format_master(item); validate_threads_reply(item,reply)

    def test_text_visual_reply_rejects_missing_or_wrong_answer_and_missing_learning_point(self):
        x=common("text"); x.update(choices=["wrong","right"],explanation="短い説明です。",
            completed_sentence="Test right now.",japanese_translation="短い訳です。",
            instagram_caption="caption",threads_parent_text="hook",visual_required=False,
            question_guide_ja="入るのはどっち？",threads_reply_explanation="短い説明です。")
        valid="💡 正解は B. right\n\n短い説明です。"
        x.update(threads_answer_text=valid,threads_reply=valid)
        for invalid in ("短い説明です。", "💡 正解は A. right\n\n短い説明です。",
                        "💡 正解は B. wrong\n\n短い説明です。"):
            with self.assertRaises(FormatValidationError):
                validate_threads_reply(x,invalid)
        missing=dict(x); missing["learning_point"]=""
        with self.assertRaises(FormatValidationError):
            validate_format_master(missing)
    def test_error_hunt_reply(self):
        x=common("error_hunt"); x.update(question="4つの英文、何個間違ってる？",correct_answer="1個",answer_mode="count")
        x["sentences"]=[{"sentence":s,"verdict":v,"corrected_sentence":c,"grammar_rule":"rule","reason_ja":r} for s,v,c,r in [("A.","CORRECT","A.","理由A"),("B.","INCORRECT","B fixed.","理由B"),("C.","CORRECT","C.","理由C"),("D.","CORRECT","D.","理由D")]]
        x["displayed_answer"]="1個"; x["answer_sentences"]=[{"verdict":r["verdict"],"corrected_sentence":r["corrected_sentence"],"reason_ja":r["reason_ja"]} for r in x["sentences"]]
        text="1個\n1 ○ A. 理由A\n2 × B fixed. 理由B\n3 ○ C. 理由C\n4 ○ D. 理由D"
        validate_format_master(x); validate_threads_reply(x,text)
        with self.assertRaises(FormatValidationError): validate_threads_reply(x,text.replace("B fixed.",""))
    def test_pattern_reply(self):
        x=common("pattern"); x.update(examples=["buy → bought","teach → taught"],target="think → ___",choices=["thought","thinked"],correct_answer="thought",pattern_rule="不規則過去形",examples_learning_point="point",target_learning_point="point")
        validate_threads_reply(x,"thought\n不規則過去形\nbuy → bought\nteach → taught")
        with self.assertRaises(FormatValidationError): validate_threads_reply(x,"thought")
    def test_save_list_reply(self):
        x=common("save_list"); rows=[{"english":f"term{i}","japanese":f"意味{i}"} for i in range(4)]
        x.update(question="基本表現",list_items=rows,target_item={"prompt":"term ___","completed":"term5","japanese":"意味5","list_theme":"基本表現"},list_theme="基本表現",choices=["right","wrong"],complete_list=rows+[{"english":"term5","japanese":"意味5"}])
        text="right\n"+"\n".join(f"{r['english']}＝{r['japanese']}" for r in x["complete_list"])
        validate_threads_reply(x,text)
        with self.assertRaises(FormatValidationError): validate_threads_reply(x,text.replace("意味3",""))
    def test_difference_reply(self):
        x=common("difference"); x.update(choices=["wrong","right"],choice_explanations={"wrong":"誤答用法","right":"正答用法"},completed_sentence="Test right now.")
        validate_threads_reply(x,"right\nwrong＝誤答用法\nright＝正答用法")
        with self.assertRaises(FormatValidationError): validate_threads_reply(x,"right＝正答用法")
    def test_schedule_contract_is_date_and_slot_driven(self):
        slots=["07:00","09:30"]
        items=[{"content_id":f"ENG-9{i:05d}","publish_at":f"2026-08-{day:02d}T{slot}:00+09:00","status":"pending"}
               for i,(day,slot) in enumerate((d,s) for d in (24,25) for s in slots)]
        validate_quiz_schedule(items,"2026-08-24","2026-08-25",slots)
    def test_old_and_new_schedule_manifests_can_coexist(self):
        slots=["07:00"]
        old={"start_date":"2026-08-24","end_date":"2026-08-24","items":[{"content_id":"ENG-900001","publish_at":"2026-08-24T07:00:00+09:00","status":"posted","content_type":"quiz"}]}
        new={"start_date":"2026-08-25","end_date":"2026-08-25","items":[{"content_id":"ENG-900002","publish_at":"2026-08-25T07:00:00+09:00","status":"pending","content_type":"quiz"}]}
        self.assertEqual(len(validate_schedule_manifests([old,new],slots)),2)

if __name__=="__main__": unittest.main()
