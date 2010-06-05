from PyQt4 import QtCore, QtGui, QtWebKit
from datetime import timedelta, datetime, date
try:
    import json
except ImportError:
    import simplejson as json
import urllib2
import os
import copy
import re
import time
import calendar

class QLineEditWithPlaceholder(QtGui.QLineEdit):
    def __init__(self, parent = None):
        QtGui.QLineEdit.__init__(self, parent)
        self.placeholder = None

    def setPlaceholderText(self, text):
        self.placeholder = text
        self.update()

    def paintEvent(self, event):
        QtGui.QLineEdit.paintEvent(self, event)
        if self.placeholder and not self.hasFocus() and not self.text():
            painter = QtGui.QPainter(self)
            painter.setPen(QtGui.QPen(QtCore.Qt.darkGray))
            painter.drawText(QtCore.QRect(8, 1, self.width(), self.height()), \
                                QtCore.Qt.AlignVCenter, self.placeholder)
            painter.end()

class QuestionDisplayWidget(QtGui.QWidget):
    

    def __init__(self, question, parent = None):
        QtGui.QWidget.__init__(self, parent)
        
        SITE_LOGOS = {'stackoverflow.com':'img/stackoverflow_logo.svg',
                      'serverfault.com':'img/serverfault_logo.svg',
                      'superuser.com':'img/superuser_logo.svg',
                      'meta.stackoverflow.com':'img/metastackoverflow_logo.svg',
                      }

        self.setGeometry(QtCore.QRect(0,0,320,80))
        self.setStyleSheet('QLabel {color: #cccccc;}')
        self.frame = QtGui.QFrame(self)
        self.frame.setObjectName('mainFrame')
        self.frame.setStyleSheet('#mainFrame {background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #333333, stop: 1 #4d4d4d);}')
        
        path = os.getcwd()
        self.question = question

        font = QtGui.QFont()
        font.setPointSize(14)

        self.question_label = QtGui.QLabel(self.frame)
        self.question_label.setGeometry(QtCore.QRect(10, 7, 280, 50))
        self.question_label.setWordWrap(True)
        self.question_label.setFont(font)
        self.question_label.setText(question.title)
        self.question_label.setObjectName('question_label')
        self.question_label.setStyleSheet("#question_label{color: #83ceea;text-decoration:underline} #question_label:hover{text-decoration:none;}")

        self.remove_button = QtGui.QPushButton(self.frame)
        self.remove_button.setGeometry(QtCore.QRect(295, 7, 25, 25))
        self.remove_button.setText('X')
        self.remove_button.setStyleSheet("QPushButton{background: #818185; border: 3px solid black; color: white;} QPushButton:hover{background: #c03434;}")
        self.remove_button.clicked.connect(self.remove)

        if question.site in SITE_LOGOS:
            self.site_icon = QtGui.QLabel(self.frame)
            self.site_icon.setGeometry(QtCore.QRect(10, 60, 25, 25))
            self.site_icon.setStyleSheet("image: url(" + path + "/" + SITE_LOGOS[question.site] + "); background-repeat:no-repeat;")

        self.answers_label = QtGui.QLabel(self.frame)
        self.answers_label.setText('%s answer(s)' % question.answer_count)
        self.answers_label.setGeometry(QtCore.QRect(40, 65, 100, 20))
        
        if question.submitter is not None:
            self.submitted_label = QtGui.QLabel(self.frame)
            self.submitted_label.setText('asked by ' + question.submitter)
            self.submitted_label.setAlignment(QtCore.Qt.AlignRight)
            self.submitted_label.setGeometry(QtCore.QRect(120, 65, 200, 20))

    def remove(self):
        self.emit(QtCore.SIGNAL('removeQuestion'), self.question)



class QuestionItem(QtGui.QWidget):
    def __init__(self, question):
        QtGui.QListWidgetItem.__init__(self)

        self.setGeometry(QtCore.QRect(0,0,325,50))
        
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setFamily("Arial")

        self.label = QtGui.QLabel(self)
        self.label.setWordWrap(True)
        self.label.setGeometry(QtCore.QRect(15,0,253,50))
        self.label.setFont(font)

        self.stop_button = QtGui.QPushButton(self)
        self.stop_button.setGeometry(QtCore.QRect(265,12,25,25))
        self.stop_button.setFont(font)
        self.stop_button.setText("X")
        self.stop_button.clicked.connect(self.remove)

        try:
            background = StackTracker.SITES[question.site]
        except KeyError:
            background = 'white'

        self.label.setStyleSheet("background: %s; border: 1px solid black; border-radius: 10px; margin: 2px; color: white;" % (background))
        self.stop_button.setStyleSheet("QPushButton{background: #cccccc; border: 1px solid black; border-radius: 5px; color: white;} QPushButton:hover{background: #c03434;}")

        self.label.setText(question.title)
        self.id = question.id
        self.question = question

    def remove(self):
        self.emit(QtCore.SIGNAL('removeQuestion'), self.question)

    def __repr__(self):
        return "%s: %s" % (self.id, self.title)


class Question():
    def __init__(self, question_id, site, title = None, created = None, last_queried = None, already_answered = None, answer_count = None, submitter = None):
        self.id = question_id
        self.site = site
        
        api_base = 'http://api.%s/%s' \
                        % (self.site, StackTracker.API_VER)
        base = 'http://%s/questions/' % (self.site)
        self.url = base + self.id

        self.answers_url = '%s/questions/%s/answers%s' \
                        % (api_base, self.id, StackTracker.API_KEY)
        self.comments_url = '%s/questions/%s/comments%s' \
                        % (api_base, self.id, StackTracker.API_KEY)
        
        self.json_url = '%s/questions/%s/%s' \
                        % (api_base, self.id, StackTracker.API_KEY)

        if title is None or answer_count is None or submitter is None or already_answered is None:
            so_data = json.loads(urllib2.urlopen(self.json_url).read())

        if title is None:
            self.title = so_data['questions'][0]['title']
        else:
            self.title = title

        if already_answered is None:
            self.already_answered = 'accepted_answer_id' in so_data['questions'][0]
        else:
            self.already_answered = already_answered
        
        if answer_count is None:
            self.answer_count = so_data['questions'][0]['answer_count']
        else:
            self.answer_count = answer_count

        if submitter is None:
            try:
                self.submitter = so_data['questions'][0]['owner']['display_name']
            except KeyError:
                self.submitter = None
        else:
            self.submitter = submitter

        if len(self.title) > 50:
            self.title = self.title[:48] + '...'

        if last_queried is None:
            self.last_queried = datetime.utcnow()
        else:
            self.last_queried = datetime.utcfromtimestamp(last_queried)

        if created is None:
            self.created = datetime.utcnow()
        else:
            self.created = datetime.utcfromtimestamp(created)
        
    def __repr__(self):
        return "%s: %s" % (self.id, self.title)

    def __eq__(self, other):
        return ((self.site == other.site) and (self.id == other.id))

class QSpinBoxRadioButton(QtGui.QRadioButton):
    def __init__(self, prefix = '', suffix = '', parent = None):
        QtGui.QRadioButton.__init__(self, parent)
        self.prefix = QtGui.QLabel(prefix)
        self.suffix = QtGui.QLabel(suffix)

        self.spinbox = QtGui.QSpinBox()
        self.spinbox.setEnabled(self.isDown())
        self.toggled.connect(self.spinbox.setEnabled)

        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.prefix)
        self.layout.addWidget(self.spinbox)
        self.layout.addWidget(self.suffix)
        self.layout.addStretch(2)
        self.layout.setContentsMargins(25, 0, 0, 0)

        self.setLayout(self.layout)

    def setPrefix(self, p):
        self.prefix.setText(p)

    def setSuffix(self, s):
        self.suffix.setText(s)

    def setSpinBoxSuffix(self, text):
        self.spinbox.setSuffix(" %s" % text)

    def setMinimum(self, value):
        self.spinbox.setMinimum(value)

    def setMaximum(self, value):
        self.spinbox.setMaximum(value)

    def setSingleStep(self, step):
        self.spinbox.setSingleStep(step)

    def value(self):
        return self.spinbox.value()

    def setValue(self, value):
        self.spinbox.setValue(value)

class OptionsDialog(QtGui.QDialog):
    def __init__(self, parent = None):
        QtGui.QDialog.__init__(self, parent)
        self.setFixedSize(QtCore.QSize(400,250))
        self.setWindowTitle('Options')

        self.layout = QtGui.QVBoxLayout()

        self.auto_remove = QtGui.QGroupBox("Automatically remove questions?", self)
        self.auto_remove.setCheckable(True)
        self.auto_remove.setChecked(False)
        
        self.accepted_option = QtGui.QRadioButton("When an answer has been accepted")
        
        self.time_option = QSpinBoxRadioButton('After','of being added')
        self.time_option.setMinimum(1)
        self.time_option.setMaximum(1000)
        self.time_option.setSingleStep(1)
        self.time_option.setSpinBoxSuffix(" hour(s)")
        
        self.inactivity_option = QSpinBoxRadioButton('After', 'of inactivity')
        self.inactivity_option.setMinimum(1)
        self.inactivity_option.setMaximum(1000)
        self.inactivity_option.setSingleStep(1)
        self.inactivity_option.setSpinBoxSuffix(" hour(s)")

        self.auto_layout = QtGui.QVBoxLayout()
        self.auto_layout.addWidget(self.accepted_option)
        self.auto_layout.addWidget(self.time_option)
        self.auto_layout.addWidget(self.inactivity_option)
 
        self.auto_remove.setLayout(self.auto_layout)

        self.update_interval = QtGui.QGroupBox("Update Interval", self)
        self.update_input = QtGui.QSpinBox()
        self.update_input.setMinimum(30)
        self.update_input.setMaximum(86400)
        self.update_input.setSingleStep(15)
        self.update_input.setSuffix(" seconds")
        self.update_input.setPrefix("Check for updates every ")

        self.update_layout = QtGui.QVBoxLayout()
        self.update_layout.addWidget(self.update_input)
        
        self.update_interval.setLayout(self.update_layout)

        self.buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel | QtGui.QDialogButtonBox.Save)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.layout.addWidget(self.auto_remove)
        self.layout.addWidget(self.update_interval)
        self.layout.addStretch(2)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)

    def updateSettings(self, settings):
        #todo throw this in a try block
        self.auto_remove.setChecked(settings['auto_remove'])
        self.accepted_option.setChecked(settings['on_accepted'])
        if settings['on_time']:
            self.time_option.setValue(settings['on_time'])
            self.time_option.setChecked(True)
        if settings['on_inactivity']:
            self.inactivity_option.setValue(settings['on_inactivity'])
            self.inactivity_option.setChecked(True)
        self.update_input.setValue(settings['on_time'])

    def getSettings(self):
        settings = {}
        settings['auto_remove'] = self.auto_remove.isChecked()
        settings['on_accepted'] = self.accepted_option.isChecked()
        settings['on_time'] = self.time_option.value() if self.time_option.isChecked() else False
        settings['on_inactivity'] = self.inactivity_option.value() if self.inactivity_option.isChecked() else False
        settings['update_interval'] = self.update_input.value()

        return settings

class StackTracker(QtGui.QDialog):
    
    SITES = {'stackoverflow.com':'#ff9900',
            'serverfault.com':'#ea292c',
            'superuser.com':'#00bff3',
            'meta.stackoverflow.com':'#a6a6a6',
            }

    API_KEY = '?key=Jv8tIPTrRUOqRe-5lk4myw'
    API_VER = '0.8'

    def __init__(self, parent = None):
        QtGui.QDialog.__init__(self)
        self.parent = parent
        self.setWindowTitle("StackTracker")
        self.closeEvent = self.cleanUp
        
        self.options_dialog = OptionsDialog(self)
        self.options_dialog.accepted.connect(self.serializeOptions)
        self.options_dialog.accepted.connect(self.applySettings)
        self.options_dialog.rejected.connect(self.deserializeOptions)
        self.deserializeOptions()        

        self.setGeometry(QtCore.QRect(0, 0, 325, 400))
        self.setFixedSize(QtCore.QSize(350,400))
        self.display_list = QtGui.QListWidget(self)
        self.display_list.resize(QtCore.QSize(350, 350))
        self.display_list.setStyleSheet("QListWidget{show-decoration-selected: 0; background: black;}")
        self.display_list.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.display_list.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.display_list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self.question_input = QLineEditWithPlaceholder(self)
        self.question_input.setGeometry(QtCore.QRect(15, 360, 220, 30))
        self.question_input.setPlaceholderText("Enter Question URL...")

        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setFamily("Arial")

        self.track_button = QtGui.QPushButton(self)
        self.track_button.setGeometry(QtCore.QRect(245, 360, 65, 30))
        self.track_button.setText("Track")
        self.track_button.clicked.connect(self.addQuestion)
        self.track_button.setFont(font)
        self.track_button.setStyleSheet("QPushButton{background: #e2e2e2; border: 1px solid #888888; color: black;} QPushButton:hover{background: #d6d6d6;}")
        
        self.tracking_list = []
 
        self.deserializeQuestions() #load persisted questions from tracking.json

        self.displayQuestions()


        path = os.getcwd() 
        self.notifier = QtGui.QSystemTrayIcon(QtGui.QIcon(path+'/st.png'), self)
        self.notifier.messageClicked.connect(self.popupClicked)
        self.notifier.activated.connect(self.trayClicked)
        self.notifier.setToolTip('StackTracker')
        
        self.tray_menu = QtGui.QMenu()
        self.show_action = QtGui.QAction('Show', None)
        self.show_action.triggered.connect(self.showWindow)
        
        self.options_action = QtGui.QAction('Options', None)
        self.options_action.triggered.connect(self.showOptions)
        
        self.about_action = QtGui.QAction('About', None)
        self.about_action.triggered.connect(self.showAbout)        
        
        self.exit_action = QtGui.QAction('Exit', None)
        self.exit_action.triggered.connect(self.exitFromTray)

        self.tray_menu.addAction(self.show_action)
        self.tray_menu.addAction(self.options_action)
        self.tray_menu.addAction(self.about_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.exit_action)

        self.notifier.setContextMenu(self.tray_menu)        
        self.notifier.show()

        self.worker = WorkerThread(self.tracking_list)
        self.connect(self.worker, QtCore.SIGNAL('newAnswer'), self.newAnswer)
        self.connect(self.worker, QtCore.SIGNAL('newComment'), self.newComment)
        self.connect(self.worker, QtCore.SIGNAL('autoRemove'), self.removeQuestion)

        self.applySettings()

        self.worker.start()

    def applySettings(self):
        settings = self.options_dialog.getSettings()
        interval = settings['update_interval'] * 1000 #convert to milliseconds
        self.worker.setInterval(interval)
        self.worker.applySettings(settings)

    def trayClicked(self, event):
        if event == QtGui.QSystemTrayIcon.DoubleClick:
            self.showWindow()

    def showWindow(self):
        self.show()
        self.showMaximized()
        self.displayQuestions()

    def showOptions(self):
        self.options_dialog.show()

    def showAbout(self):
        s = """
            <h3>StackTracker</h3>
            <p>A desktop notifier using the StackExchange API built with PyQt4</p>
            <p>Get alerts when answers or comments are posted to questions you are tracking.</p>
            <p><b>Created by Matt Swanson</b></p>
                        """
        QtGui.QMessageBox(1, "About",  s).exec_()

    def exitFromTray(self):
        self.cleanUp(None)
        self.parent.exit()

    def cleanUp(self, event):
        self.serializeQuestions()
        self.serializeOptions()

    def serializeQuestions(self):
        datetime_to_json = lambda obj: calendar.timegm(obj.utctimetuple()) if isinstance(obj, datetime) else None
        a = []
        for q in self.tracking_list:
            a.append(q.__dict__)
 
        with open('tracking.json', 'w') as fp:
                json.dump({'questions':a}, fp, default = datetime_to_json, indent = 4)

    def deserializeQuestions(self):
        try:
            with open('tracking.json', 'r') as fp:
                data = fp.read()
        except EnvironmentError:
            #no tracking.json file
            return

        question_data = json.loads(data)
        for q in question_data['questions']:
            rebuilt_question = Question(q['id'], q['site'], q['title'], q['created'], \
                                                q['last_queried'], q['already_answered'], 
                                                q['answer_count'], q['submitter'])
            self.tracking_list.append(rebuilt_question)

    def serializeOptions(self):
        settings = self.options_dialog.getSettings()
        with open('settings.json', 'w') as fp:
            json.dump(settings, fp, indent = 4)

    def deserializeOptions(self):
        try:
            with open('settings.json', 'r') as fp:
                data = fp.read()
        except EnvironmentError:
            return

        self.options_dialog.updateSettings(json.loads(data))

    def newAnswer(self, question):
        self.popupUrl = question.url
        self.notify("New answer(s): %s" % question.title)

    def newComment(self, question):
        self.popupUrl = question.url
        self.notify("New comment(s): %s" % question.title)

    def popupClicked(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.popupUrl))

    def displayQuestions(self):
        self.display_list.clear()
        n = 0
        for question in self.tracking_list:
            item = QtGui.QListWidgetItem(self.display_list)
            item.setSizeHint(QtCore.QSize(320, 95))
            self.display_list.addItem(item)
            qitem = QuestionDisplayWidget(question)
            self.connect(qitem, QtCore.SIGNAL('removeQuestion'), self.removeQuestion)
            self.display_list.setItemWidget(item, qitem)
            n = n + 1

    def autoRemoveQuestion(self, q):
        for question in self.tracking_list[:]:
            if question == q:
                self.tracking_list.remove(question)
        self.displayQuestions()
        self.worker.updateTrackingList(self.tracking_list)

    def removeQuestion(self, q):
        for question in self.tracking_list:
            if question == q:
                self.tracking_list.remove(question)
        self.displayQuestions()
        self.worker.updateTrackingList(self.tracking_list)

    def extractDetails(self, url):
        regex = re.compile("""(?:http://)?(?:www\.)?
                                (?P<site>(?:[A-Za-z\.])*\.[A-Za-z]*)
                                /.*?
                                (?P<id>[0-9]+)
                                /.*""", re.VERBOSE)
        match = regex.match(url)
        if match is None:
            return None
        try:
            site = match.group('site')
            id = match.group('id')
        except IndexError:
            return None
        return id, site

    def addQuestion(self):
        url = self.question_input.text()
        details = self.extractDetails(str(url))
        if details:
            id, site = details
        else:
            #bad input
            return
        #not right, fix this
        #if id not in self.tracking_list:
        if True:
            q = Question(id, site)
            self.tracking_list.append(q)
            self.displayQuestions()
            self.worker.updateTrackingList(self.tracking_list)
            self.question_input.clear()
        else:
            #question already being tracked
            return
    
    def notify(self, msg):
        self.notifier.showMessage("StackTracker", msg, self.worker.timer.interval())

class WorkerThread(QtCore.QThread):
    def __init__(self, tracking_list, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.tracking_list = tracking_list
        self.timer = QtCore.QTimer()
        self.timer.setInterval(30000)
        self.settings = {}

    def run(self):
        self.fetch()
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.fetch, QtCore.Qt.DirectConnection)
        self.timer.start(self.timer.interval())
        self.exec_()

    def __del__(self):
        self.exit()
        self.terminate()

    def setInterval(self, value):
        self.timer.setInterval(value)

    def applySettings(self, settings):
        self.settings = settings

    def updateTrackingList(self, tracking_list):
        self.tracking_list = tracking_list

    def fetch(self):
        #todo: better handling of multiple new answers with regards
        #notifications and timestamps

        #todo: sort by newest answers and break out once we get to the old answers
        #to speed up
        for question in self.tracking_list:
            new_answers = False
            new_comments = False
            most_recent = question.last_queried
            
            so_data = json.loads(urllib2.urlopen(question.answers_url).read())
            question.answer_count = so_data['total']
            for answer in so_data['answers']:
                updated = datetime.utcfromtimestamp(answer['creation_date'])
                if updated > question.last_queried:
                    new_answers = True
                    if updated > most_recent:
                        most_recent = updated

            so_data = json.loads(urllib2.urlopen(question.comments_url).read())
            for comment in so_data['comments']:
                updated = datetime.utcfromtimestamp(comment['creation_date'])
                if updated > question.last_queried:
                    new_comments = True
                    if updated > most_recent:
                        most_recent = updated
            
            if new_answers:
                self.emit(QtCore.SIGNAL('newAnswer'), question)
            if new_comments:
                self.emit(QtCore.SIGNAL('newComment'), question)

            question.last_queried = most_recent

        self.autoRemoveQuestions()

    def autoRemoveQuestions(self):
        tracking_list = copy.deepcopy(self.tracking_list)
        if self.settings['auto_remove']: #if autoremove is enabled
            if self.settings['on_accepted']: #remove when accepted
                for question in tracking_list:
                    so_data = json.loads(urllib2.urlopen(question.json_url).read())
                    if 'accepted_answer_id' in so_data['questions'][0]:
                        if not question.already_answered:
                            self.emit(QtCore.SIGNAL('autoRemove'), question)
            elif self.settings['on_inactivity']: #remove if time - last_queried > threshold
                threshold = timedelta(hours = self.settings['on_inactivity'])
                for question in tracking_list:
                    if datetime.utcnow() - question.last_queried > threshold:
                        self.emit(QtCore.SIGNAL('autoRemove'), question)
            elif self.settings['on_time']: #remove if time - created > threshold
                threshold = timedelta(hours = self.settings['on_time'])
                for question in tracking_list:
                    if datetime.utcnow() - question.created > threshold:
                        self.emit(QtCore.SIGNAL('autoRemove'), question)

if __name__ == "__main__":
    
    import sys

    app = QtGui.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    st = StackTracker(app)
    app.exec_()
    del st
    sys.exit()
