"""Real-input indexing and estimator regression checks; no simulated measurements."""
import json
import unittest

import calibrate_consensus as C
from calibrate_social import load_inputs
from calibration_common import ground_truth


class ConsensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all_rows,_,snapshot,_,_,_=load_inputs()
        C.attach_hashes(cls.all_rows,snapshot)
        cls.labels_path=C.ROOT/'scripts/narrative/labels_assistant.csv'
        probability,_,cls.population,cls.labels=ground_truth(cls.all_rows,cls.labels_path)
        cls.probability=staticmethod(probability)
        cls.rows=cls.all_rows[:80]
        cls.masks,cls.audit=C.build_pairs(cls.rows,cls.probability,cls.labels)

    def test_index_completeness_and_implicit_negative_frame(self):
        positive=0
        for j,b in enumerate(self.rows):
            for i,a in enumerate(self.rows[:j]):
                self.assertEqual(self.masks[j].get(i,0),C.signal_mask(a,b))
                positive+=self.probability(a,b)
        n=len(self.rows)*(len(self.rows)-1)//2
        self.assertAlmostEqual(self.audit['estimated_negative_pair_weight'],n-positive,places=8)
        self.assertAlmostEqual(sum(self.audit['estimated_negative_mask_histogram']),n-positive,places=8)

    def test_missing_images_and_posts_never_cast_votes(self):
        j,i=next((j,i) for j,m in enumerate(self.masks) for i,mask in m.items() if mask&C.IMAGE)
        a={**self.rows[i],'hash_int':None,'social':{'x_post':set()}}
        b={**self.rows[j],'hash_int':None,'social':{'x_post':set()}}
        self.assertEqual(C.signal_mask(a,b)&(C.IMAGE|C.POST),0)

    def test_mutually_exclusive_votes_and_unreachable_threshold(self):
        for row in self.masks:
            for mask in row.values():
                self.assertFalse(mask&C.SYMBOL and mask&C.EDIT)
                self.assertLessEqual(mask.bit_count(),5)
                self.assertLessEqual((mask&C.NO_IMAGE).bit_count(),4)
        routes,_=C.replay(self.rows,self.masks,k=6)
        self.assertEqual(routes,[])
        baseline,_=C.replay(self.rows,self.masks)
        combined,_=C.replay(self.rows,self.masks,k=6,combined=True)
        self.assertEqual(baseline,combined)

    def test_archival_population_preserved_and_missing_uri_sensitivity_explicit(self):
        _,certain,pop,_,details=ground_truth(self.all_rows,self.labels_path,details=True)
        self.assertEqual(pop,self.population)
        self.assertEqual(sum(details['copy_probabilities']),pop)
        reference=json.loads((C.OUT/'label_dependency.json').read_text(encoding='utf-8'))
        self.assertEqual(pop,reference['legacy_expected_vamps'])
        _,clean_certain,clean_pop,_,_=ground_truth(self.all_rows,self.labels_path,exclude_missing_uri=True,details=True)
        self.assertLess(clean_pop,pop)
        self.assertLess(len(clean_certain),len(certain))
        missing=[r for r in self.all_rows if not r['uri']]
        for b in missing:
            for a in missing:
                self.assertNotEqual(C.truth_source(a,b,self.labels,exclude_missing=True),'legacy_empty_uri_definition')


if __name__=='__main__':
    unittest.main()
