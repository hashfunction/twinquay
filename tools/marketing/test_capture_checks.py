"""Real input receipt boundary refusals; full downloaded package verified separately."""
import copy
import unittest
import capture_checks as c

class Receipts(unittest.TestCase):
    def setUp(self):
        self.ready={'source_commit':c.SOURCE,'workflow_run_id':c.RUN,'workflow_run_attempt':'1',
            'store_upload_ready':True,'signed':False,'identity':c.LOCKED_IDENTITY,
            'package':dict(c.PACKAGE,filename=c.PACKAGE_NAME),'qualified_identity_modes':['qualification','store'],
            'qualification_evidence':{'msix-store-package-record.json':{'bytes':1,'sha256':'0'*64}}}
        self.run={'id':int(c.RUN),'head_sha':c.SOURCE,'run_attempt':1,'conclusion':'success',
            'repository':{'full_name':'hashfunction/twinquay'},'path':'.github/workflows/windows.yml'}
    def test_valid_receipts(self): c.validate_receipts(self.ready,self.run)
    def test_changed_readiness(self):
        for key,value in {'store_upload_ready':False,'signed':True,'source_commit':'f'*40,'workflow_run_id':'1',
            'workflow_run_attempt':'2','package':{},'identity':{},'qualified_identity_modes':['store'],'qualification_evidence':{}}.items():
            with self.subTest(key=key):
                changed=copy.deepcopy(self.ready);changed[key]=value
                with self.assertRaises(ValueError):c.validate_receipts(changed,self.run)
    def test_changed_run(self):
        for key,value in {'id':1,'head_sha':'0'*40,'run_attempt':2,'conclusion':'failure','repository':{},'path':'different.yml'}.items():
            with self.subTest(key=key):
                changed=copy.deepcopy(self.run);changed[key]=value
                with self.assertRaises(ValueError):c.validate_receipts(self.ready,changed)
    def test_paths(self):
        for name in ('../secret','/absolute','c:x','a\\b','a//b','a/./b',''):
            with self.assertRaises(ValueError):c.relative_path(name)

if __name__=='__main__':unittest.main()
