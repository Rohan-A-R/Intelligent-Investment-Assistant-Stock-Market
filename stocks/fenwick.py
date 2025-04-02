class FenwickTree:
    def __init__(self, size):
        self.size = size
        self.tree = [0] * (size + 1)  # 1-based indexing

    def _lsb(self, i):
        return i & (-i)  # Least significant bit

    def update(self, index, value):
        i = index + 1  # Convert to 1-based
        while i <= self.size:
            self.tree[i] += value
            i += self._lsb(i)

    def query(self, index):
        i = index + 1  # Convert to 1-based
        total = 0
        while i > 0:
            total += self.tree[i]
            i -= self._lsb(i)
        return total

    def range_query(self, left, right):
        return self.query(right) - self.query(left - 1)