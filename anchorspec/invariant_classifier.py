"""Weighted empirical distributions: exact replication is not new evidence."""
import math
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from scipy.special import softmax


def canonicalize(x,y,w):
    x=np.asarray(x,float);y=np.asarray(y);w=np.asarray(w,float)
    if x.ndim!=2 or y.shape!=(len(x),) or w.shape!=(len(x),) or not np.isfinite(x).all() or not np.isfinite(w).all() or np.any(w<0):
        raise ValueError('Invalid weighted data')
    if not np.issubdtype(y.dtype,np.integer) or np.any((y<0)|(y>4)):raise ValueError('Invalid class labels')
    positive=w>0;x,y,w=x[positive],y[positive],w[positive]
    if not len(w):raise ValueError('Positive training mass required')
    total=round(math.fsum(w),10)
    if total<=0:raise ValueError('Insufficient training mass')
    rows,inverse=np.unique(np.column_stack((x,y)),axis=0,return_inverse=True)
    weights=np.array([math.fsum(w[inverse==i]) for i in range(len(rows))])
    weights=np.round(weights/math.fsum(weights),14)
    weights*=total/math.fsum(weights)
    return rows[:,:-1],rows[:,-1].astype(int),weights


class InvariantClassifier:
    def __init__(self,family='svm1',seed=11):
        if family not in ('svm1','svm10','rf'):raise ValueError('Unknown family')
        self.family,self.seed=family,seed

    def fit(self,x,y,w):
        x,y,w=canonicalize(x,y,w)
        self.classes_=np.unique(y);self.total_weight_=float(w.sum());self.unique_rows_=len(y)
        self.scaler_=StandardScaler().fit(x,sample_weight=w);z=self.scaler_.transform(x)
        self.model_=None
        if len(self.classes_)>1:
            if self.family=='rf':
                self.model_=RandomForestClassifier(n_estimators=50,max_depth=8,min_samples_leaf=1,
                    min_weight_fraction_leaf=.01,max_features='sqrt',bootstrap=False,n_jobs=1,random_state=self.seed)
            else:self.model_=SVC(C=1 if self.family=='svm1' else 10,gamma=1/x.shape[1],decision_function_shape='ovr')
            self.model_.fit(z,y,sample_weight=w)
        return self

    def predict_proba(self,x):
        z=self.scaler_.transform(x)
        if self.model_ is None:p=np.ones((len(z),1))
        elif self.family=='rf':p=self.model_.predict_proba(z)
        else:
            scores=self.model_.decision_function(z)
            if len(self.classes_)==2:scores=np.column_stack((-scores,scores))
            p=softmax(scores,axis=1)
        out=np.zeros((len(z),5));out[:,self.classes_]=p
        return out
