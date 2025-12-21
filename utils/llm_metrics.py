class LLMMetrics:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_time = 0.0
        self.calls = 0

    def add(self, input_tokens=0, output_tokens=0, response_time=0.0):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_time += response_time
        self.calls += 1

    @property
    def total_tokens(self):
        return self.total_input_tokens + self.total_output_tokens

    def to_dict(self):
        return {
            "calls": self.calls,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_time": self.total_time,
        }
