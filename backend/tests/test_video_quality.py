import copy
import json
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch
from backend.services.director import script_to_video,build_direction,direct_scene
from backend.services.editor_store import document_from_video,quality,validate_document
from backend.tests.test_director import SCRIPT

class VideoQualityTests(unittest.TestCase):
    def test_old_empty_code_remains_editable_but_blocks_export(self):
        doc=document_from_video(script_to_video('Library',SCRIPT))
        doc['scenes'][0]['visual']={'kind':'code','items':[]}
        validate_document(doc)
        self.assertIn('missing_code',{i['code'] for i in quality(doc)['issues']})
        doc['scenes'][0]['visual']['codeLines']=['print("hello")']
        self.assertNotIn('missing_code',{i['code'] for i in quality(doc)['issues']})

    def test_unsupported_statistics_are_flagged_without_losing_saved_content(self):
        doc=document_from_video(script_to_video('Library',SCRIPT))
        doc['scenes'][0]['visual']={'kind':'stat_card','items':['Volume','Latency'],'values':[100,65]}
        validate_document(doc)
        issues=quality(doc)['issues']
        self.assertTrue(any(i['code']=='unsupported_statistic' and i['severity']=='error' for i in issues))
        row=doc['scenes'][0]
        row['narration']='In this fictional library example, 100 books are available today. Of those books, 65 are borrowed by readers during the week.'
        self.assertNotIn('unsupported_statistic',{i['code'] for i in quality(doc)['issues']})

    def test_keyword_fallback_never_invents_cost_numbers_or_placeholder_code(self):
        scene=script_to_video('Library',SCRIPT).scenes[1]
        for text in ['More tokens usually mean more work and higher cost and performance demands for a model processing a long request.', 'Code can also be split into tokens. Symbols, punctuation, operators and variable names form parts of the input.']:
            row=direct_scene(scene.model_copy(update={'headline':'A practical mechanism','narration':text}),1,4)
            self.assertNotIn(row['kind'],{'stat_card','code'})
            self.assertNotIn('values',row)

    def test_chapter_join_preserves_bookend_silence_and_scene_offsets(self):
        from backend.scripts import long_video_worker as worker
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);audio=root/'renderer/public/audio';audio.mkdir(parents=True)
            with wave.open(str(audio/'scene-1.wav'),'wb') as stream:
                stream.setparams((1,2,24000,0,'NONE','not compressed'));stream.writeframes(b'\x01\x00'*24000)
            chapters=[]
            for i in range(2):
                folder=root/f'chapter-{i}';folder.mkdir();chapters.append(str(folder))
                props={'videoData':{'scenes':[{'id':1,'duration':1,'audio':'audio/scene-1.wav'}],
                    'style':{'showIntro':i==0,'showOutro':i==1}}}
                (folder/'draft-props.json').write_text(json.dumps(props))
            manifest=root/'join.json';manifest.write_text(json.dumps({'profile':'draft','chapters':chapters,'output':str(root/'joined.mp4')}))
            with patch.object(worker,'ROOT',root),patch.object(worker.subprocess,'run'),patch('backend.scripts.validate_render.validate',return_value={'videoDuration':11}):
                worker.join(manifest)
            with wave.open(str(root/'combined-narration.wav'),'rb') as stream:
                self.assertEqual(stream.getnframes(),11*24000)
                self.assertEqual(stream.readframes(3*24000),b'\0\0'*(3*24000))
                self.assertEqual(stream.readframes(1),b'\x01\x00')
            combined=json.loads((root/'draft-combined-props.json').read_text())['videoData']
            self.assertTrue(combined['style']['showIntro']);self.assertTrue(combined['style']['showOutro'])

if __name__=='__main__':unittest.main()
