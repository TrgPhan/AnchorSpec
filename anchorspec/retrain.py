"""Vòng học lại cục bộ có rào chắn theo kế hoạch v1.4 (M4).

Quy tắc: chỉ học lô kỹ sư xác nhận; luôn giữ lỗi cấy và lỗi cũ; bản mới chỉ thay khi không
kém trên bộ kiểm tra cố định; có đánh số phiên bản, quay lại được; thay/gá lại cảm biến là
hiệu chuẩn nền, không phải học lỗi. Lớp này KHÔNG tự chạy trên dòng dữ liệu.
"""
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import RandomForestClassifier


@dataclass
class Version:
    number: int
    model: object
    n_confirmed: int
    fixed_score: float
    note: str


@dataclass
class MachineModel:
    """Đặc trưng lưu ở dạng thô để có thể chuẩn hóa lại khi hiệu chuẩn nền."""
    base: np.ndarray
    injected: np.ndarray
    injected_y: np.ndarray
    fixed_x: np.ndarray
    fixed_y: np.ndarray
    n_classes: int = 4
    real_mass: float = .5
    min_batch: int = 3
    tolerance: float = .02
    seed: int = 0
    cfg: dict = field(default_factory=lambda: dict(n_estimators=50, max_depth=8, min_samples_leaf=2, max_features='sqrt', bootstrap=False, n_jobs=1))
    confirmed_x: list = field(default_factory=list)
    confirmed_y: list = field(default_factory=list)
    versions: list = field(default_factory=list)
    active: int = -1
    log: list = field(default_factory=list)

    def __post_init__(self):
        self._set_norm(self.base)
        model = self._fit(self.confirmed_x, self.confirmed_y)
        self.versions.append(Version(1, model, 0, self._score(model), 'goc'))
        self.active = 0

    def _set_norm(self, base):
        self.mu, self.sd = base.mean(0), base.std(0)+1e-9

    def _z(self, x):
        return (x-self.mu)/self.sd

    def _fit(self, xs, ys):
        """Mỗi lớp tổng trọng số 1; lớp có lỗi thật xác nhận thì thật chiếm real_mass."""
        X = [self._z(self.base), self._z(self.injected)]
        y = [np.zeros(len(self.base), int), self.injected_y]
        cx = np.concatenate(xs) if xs else np.zeros((0, self.base.shape[1]))
        cy = np.concatenate(ys) if ys else np.zeros(0, int)
        w = [np.full(len(self.base), 1/len(self.base))]
        syn = np.zeros(len(self.injected_y))
        for k in np.unique(self.injected_y):
            mask = self.injected_y == k
            mass = 1-self.real_mass if (cy == k).any() else 1.
            syn[mask] = mass/mask.sum()
        w.append(syn)
        if len(cy):
            X.append(self._z(cx))
            y.append(cy)
            real = np.zeros(len(cy))
            for k in np.unique(cy):
                real[cy == k] = (self.real_mass if (self.injected_y == k).any() else 1.)/(cy == k).sum()
            w.append(real)
        return RandomForestClassifier(random_state=self.seed, **self.cfg).fit(np.concatenate(X), np.concatenate(y), sample_weight=np.concatenate(w))

    def _score(self, model):
        return float((model.predict(self._z(self.fixed_x)) == self.fixed_y).mean())

    @property
    def model(self):
        return self.versions[self.active].model

    def predict_proba(self, x):
        p = np.zeros((len(x), self.n_classes))
        p[:, self.model.classes_] = self.model.predict_proba(self._z(x))
        return p

    def propose(self, x, y, confirmed_by):
        """Một lô. Trả (chấp nhận?, lý do). Từ chối không làm mất dữ liệu đang dùng."""
        if not confirmed_by:
            return self._reject('chua_co_ky_su_xac_nhan')
        if len(x) < self.min_batch:
            return self._reject('lo_qua_nho')
        new_x, new_y = self.confirmed_x+[x], self.confirmed_y+[np.asarray(y, int)]
        model = self._fit(new_x, new_y)
        current, score = self.versions[self.active].fixed_score, self._score(model)
        if score < current-self.tolerance:
            return self._reject(f'kem_hon_tren_bo_co_dinh:{score:.3f}<{current:.3f}')
        if self.confirmed_x:
            old = np.concatenate(self.confirmed_x)
            old_y = np.concatenate(self.confirmed_y)
            before = (self.model.predict(self._z(old)) == old_y).mean()
            after = (model.predict(self._z(old)) == old_y).mean()
            if after < before-self.tolerance:
                return self._reject(f'quen_loi_cu:{after:.3f}<{before:.3f}')
        self.confirmed_x, self.confirmed_y = new_x, new_y
        self.versions.append(Version(len(self.versions)+1, model, sum(map(len, new_x)), score, f'xac_nhan_boi:{confirmed_by}'))
        self.active = len(self.versions)-1
        self.log.append(('accept', self.versions[-1].number))
        return True, 'chap_nhan'

    def _reject(self, why):
        self.log.append(('reject', why))
        return False, why

    def rollback(self, number):
        """Quay về một phiên bản đã có; dữ liệu xác nhận vẫn được giữ."""
        for i, v in enumerate(self.versions):
            if v.number == number:
                self.active = i
                self.log.append(('rollback', number))
                return
        raise ValueError(f'Khong co phien ban {number}')

    def recalibrate(self, new_base):
        """Thay hoặc gá lại cảm biến: đổi nền, huấn luyện lại; KHÔNG thêm nhãn lỗi."""
        self.base = new_base
        self._set_norm(new_base)
        model = self._fit(self.confirmed_x, self.confirmed_y)
        self.versions.append(Version(len(self.versions)+1, model, sum(map(len, self.confirmed_x)), self._score(model), 'hieu_chuan_nen'))
        self.active = len(self.versions)-1
        self.log.append(('recalibrate', self.versions[-1].number))
