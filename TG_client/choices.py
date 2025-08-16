
class TaskAction:
    LISTEN = "LISTEN"
    PARSE = "PARSE"

    CHOICES = (
        (LISTEN, "Listen"),
        (PARSE, "Parse messages"),
    )

    LIST = [ch[0] for ch in CHOICES]


class TaskStatus:
    DRAFT = "DRAFT"
    CHECK = "CHECK"
    READY = "READY"
    RUN = "RUN"
    STOP = "STOP"
    FINISH = "FINISH"
    WAIT = "WAIT"

    CHOICES = (
        (DRAFT, "Draft"),
        (CHECK, "Check"),
        (READY, "Ready"),
        (RUN, "Run"),
        (STOP, "Stop"),
        (FINISH, "Finish"),
        (WAIT, "Wait"),
    )

    LIST = [ch[0] for ch in CHOICES]


TASK_TODO = {
    TaskStatus.DRAFT: "Check",
    TaskStatus.CHECK: "Abort",
    TaskStatus.READY: "Start",
    TaskStatus.RUN: "Stop",
    TaskStatus.STOP: "Start",
    TaskStatus.FINISH: "Start",
    TaskStatus.WAIT: "Cancel",
}
