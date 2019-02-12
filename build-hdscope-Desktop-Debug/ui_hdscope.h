/********************************************************************************
** Form generated from reading UI file 'hdscope.ui'
**
** Created by: Qt User Interface Compiler version 5.11.1
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_HDSCOPE_H
#define UI_HDSCOPE_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QMenuBar>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QStatusBar>
#include <QtWidgets/QWidget>
#include "mplwidget.h"

QT_BEGIN_NAMESPACE

class Ui_MainWindow
{
public:
    QWidget *centralwidget;
    QWidget *horizontalLayoutWidget;
    QHBoxLayout *horizontalLayout;
    QSpacerItem *horizontalSpacer_2;
    QCheckBox *ch1;
    QCheckBox *ch2;
    QCheckBox *ch3;
    QCheckBox *ch4;
    QSpacerItem *horizontalSpacer;
    MplWidget *MplWidget;
    QMenuBar *menubar;
    QStatusBar *statusbar;

    void setupUi(QMainWindow *MainWindow)
    {
        if (MainWindow->objectName().isEmpty())
            MainWindow->setObjectName(QStringLiteral("MainWindow"));
        MainWindow->resize(800, 600);
        centralwidget = new QWidget(MainWindow);
        centralwidget->setObjectName(QStringLiteral("centralwidget"));
        horizontalLayoutWidget = new QWidget(centralwidget);
        horizontalLayoutWidget->setObjectName(QStringLiteral("horizontalLayoutWidget"));
        horizontalLayoutWidget->setGeometry(QRect(210, 0, 446, 31));
        horizontalLayout = new QHBoxLayout(horizontalLayoutWidget);
        horizontalLayout->setObjectName(QStringLiteral("horizontalLayout"));
        horizontalLayout->setContentsMargins(0, 0, 0, 0);
        horizontalSpacer_2 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout->addItem(horizontalSpacer_2);

        ch1 = new QCheckBox(horizontalLayoutWidget);
        ch1->setObjectName(QStringLiteral("ch1"));

        horizontalLayout->addWidget(ch1);

        ch2 = new QCheckBox(horizontalLayoutWidget);
        ch2->setObjectName(QStringLiteral("ch2"));

        horizontalLayout->addWidget(ch2);

        ch3 = new QCheckBox(horizontalLayoutWidget);
        ch3->setObjectName(QStringLiteral("ch3"));

        horizontalLayout->addWidget(ch3);

        ch4 = new QCheckBox(horizontalLayoutWidget);
        ch4->setObjectName(QStringLiteral("ch4"));

        horizontalLayout->addWidget(ch4);

        horizontalSpacer = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout->addItem(horizontalSpacer);

        MplWidget = new MplWidget(centralwidget);
        MplWidget->setObjectName(QStringLiteral("MplWidget"));
        MplWidget->setGeometry(QRect(10, 40, 781, 501));
        MainWindow->setCentralWidget(centralwidget);
        menubar = new QMenuBar(MainWindow);
        menubar->setObjectName(QStringLiteral("menubar"));
        menubar->setGeometry(QRect(0, 0, 800, 30));
        MainWindow->setMenuBar(menubar);
        statusbar = new QStatusBar(MainWindow);
        statusbar->setObjectName(QStringLiteral("statusbar"));
        MainWindow->setStatusBar(statusbar);

        retranslateUi(MainWindow);

        QMetaObject::connectSlotsByName(MainWindow);
    } // setupUi

    void retranslateUi(QMainWindow *MainWindow)
    {
        MainWindow->setWindowTitle(QApplication::translate("MainWindow", "MainWindow", nullptr));
        ch1->setText(QApplication::translate("MainWindow", "CH1", nullptr));
        ch2->setText(QApplication::translate("MainWindow", "CH2", nullptr));
        ch3->setText(QApplication::translate("MainWindow", "CH3", nullptr));
        ch4->setText(QApplication::translate("MainWindow", "CH4", nullptr));
    } // retranslateUi

};

namespace Ui {
    class MainWindow: public Ui_MainWindow {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_HDSCOPE_H
