"""Event-selected fault diagnosis, conditional on a separate abnormal-event gate."""
from collections import defaultdict
from dataclasses import replace
import numpy as np

from adaptive_experts import transform, event_folds, fit_weighted
from event_experts import validate_events, causal_average, _prob
from kernel_experts import KernelModel


def fault_labels(p):
    scores = np.asarray(p)[:,1:]
    output = scores.argmax(1) + 1
    output[scores.sum(1) <= 0] = -1
    return output


def build(healthy, synthetic, events, mass, family, seed):
    if family == 'rf':
        return fit_weighted(healthy,synthetic,events,mass,seed)
    return KernelModel(1. if family == 'svm1' else 10.).fit(healthy,synthetic,events,mass)


def scores(model,x,family):
    return _prob(model,x,5) if family == 'rf' else model.predict_proba(x)


class DiagnosticExperts:
    def __init__(self, seed=11, real_only=False):
        self.seed,self.real_only=seed,real_only

    def fit(self,healthy,synthetic,events,*,target_id,references):
        validate_events(events,target_id)
        self.reference_=references[target_id]
        self.target_id_=target_id
        self.event_ids_=tuple(e.event_id for e in events)
        folds=event_folds(events)
        self.inner_folds_=[[e.event_id for e in f] for f in folds]
        self.validation_=[]
        for rep in ('z','delta','raw'):
            h=transform(healthy,self.reference_,rep)
            syn={c:transform(x,self.reference_,rep) for c,x in synthetic.items()}
            ev={e.event_id:replace(e,features=transform(e.features,references[e.bearing_id],rep)) for e in events}
            for family in ('rf','svm1','svm10'):
                for mass in ((0.,) if self.real_only else (0.,.1,.5)):
                    validation=defaultdict(list)
                    for fold in folds:
                        ids={e.event_id for e in fold}
                        model=build(h,syn,[ev[e.event_id] for e in events if e.event_id not in ids],mass,family,self.seed)
                        for e in fold:
                            pred=fault_labels(causal_average(scores(model,ev[e.event_id].features,family)))
                            validation[e.label].append(float((pred==e.label).mean()))
                    objective=float(np.mean([np.mean(v) for v in validation.values()])) if validation else None
                    self.validation_.append({'representation':rep,'family':family,'synthetic_mass':mass,'score':objective})
        if folds:
            best=max(self.validation_,key=lambda r:(r['score'],-r['synthetic_mass'],-('rf','svm1','svm10').index(r['family']),-('z','delta','raw').index(r['representation'])))
        else:
            best={'representation':'z','family':'rf','synthetic_mass':0. if self.real_only else .5}
        self.selection_=best
        rep=best['representation']
        self.model_=build(transform(healthy,self.reference_,rep),{c:transform(x,self.reference_,rep) for c,x in synthetic.items()},
            [replace(e,features=transform(e.features,references[e.bearing_id],rep)) for e in events],best['synthetic_mass'],best['family'],self.seed)
        return self

    def predict_proba(self,z):
        """Uncalibrated normalized scores, retained for experiment API compatibility."""
        return scores(self.model_,transform(z,self.reference_,self.selection_['representation']),self.selection_['family'])

    def diagnose(self,z,*,abnormal_event):
        if not abnormal_event:
            return np.zeros(len(z),int)
        return fault_labels(causal_average(self.predict_proba(z)))
