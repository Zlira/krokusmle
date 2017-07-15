from collections import namedtuple
import re

import pandas as pd

# question
TestQuestion = namedtuple('TestQuestion', [
    'N', 'question_text', 'A_ans', 'B_ans', 'C_ans', 'D_ans', 'E_ans'
])
TestQuestion.__new__.__defaults__ = (None,) * len(TestQuestion._fields)

# events
LineEvent = namedtuple('LineEvent', [
    'event', 'event_id', 'line_text'
])
Q_START = 'Q_START'
A_START = 'A_START'
# this is specific to USMLE test
SET_START = 'SET_START'
END = 'END'
END_OF_SET = 'END_OF_SET'
EVENTS = {
    Q_START: [re.compile(r'^(\d+)\. ')],
    A_START: [re.compile(r'^([ABCDE])\. '), re.compile(r'^\(([ABCDE])\) ')],
    SET_START: [re.compile(r'^Items (\d+.\d+)')],
    END_OF_SET: [re.compile(r'END OF SET')],
}


def parse_line_event(line):
    event, event_id = None, None
    for event_name, exprs in EVENTS.items():
        for e in exprs:
            match = e.match(line)
            if match:
                break
        if match:
            event = event_name
            if match.groups():
                event_id = match.groups()[0]
            line = e.sub('', line)
    return LineEvent(event, event_id, clean_line(line))


def clean_line(line_text):
    line_text = line_text.strip()
    # remove hyphenation at the ends of lines
    if re.findall(r'\w-$', line_text):
        line_text = line_text.rstrip('-')
    elif line_text:
        line_text += ' '
    return line_text


def iter_lines(file_path):
    with open(file_path) as f:
        next_event = parse_line_event(next(f))
        for line in f:
            curr_event, next_event = next_event, parse_line_event(line)
            yield curr_event
            if next_event.event in (Q_START, A_START):
                yield LineEvent(END, None, None)

            # skip all the text inside the USMLE set because I don't know how
            # to evaluate this
            if next_event.event == SET_START:
                while next_event.event != END_OF_SET:
                    next_event = parse_line_event(next(f))
                next_event = parse_line_event(next(f))
        # last 'END' event
        yield LineEvent(END, None, None)


def parse(file_path):
    for event, event_id, line_text in iter_lines(file_path):
        if event == Q_START:
            question = {'N': event_id}
            curr_text = line_text
            curr_attr = 'question_text'
        elif event == A_START:
            curr_text = line_text
            curr_attr = event_id + '_ans'
        elif event == END:
            question[curr_attr] = curr_text
            # this is the last answer (a bit ad hoc but will do)
            if curr_attr == 'E_ans':
                yield TestQuestion(**question)
        else:
            curr_text += line_text


def parse_df(file_path):
    parser = parse(file_path)
    return pd.DataFrame(
        list(parser), columns=TestQuestion._fields,
    )
