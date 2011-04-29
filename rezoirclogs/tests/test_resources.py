import unittest2


class BaseTests(unittest2.TestCase):
    def testRepr(self):
        from rezoirclogs.resources import Base
        b = Base()
        b.__name__ = "belong to us"
        self.assertEqual(repr(b), '<Base: belong to us>')


class FilesystemTests(unittest2.TestCase):
    def _make_one(self, *arg, **kw):
        from rezoirclogs.resources import Filesystem
        return Filesystem(*arg, **kw)

    def test_list_jail(self):
        from os.path import abspath, join, dirname
        curdir = abspath(dirname(__file__))
        jaildir = join(curdir, 'jail')
        fs = self._make_one(jaildir)
        self.assertIsNone(fs.listdir(curdir))

    def test_list(self):
        import os, tempfile
        file = tempfile.NamedTemporaryFile()
        fs = self._make_one(tempfile.tempdir)
        self.assertIn(os.path.basename(file.name), fs.listdir(tempfile.tempdir))

    def test_isrealfile_isrealdir(self):
        import os, tempfile
        file = tempfile.NamedTemporaryFile()
        link = file.name + '.link'
        os.symlink(file.name, link)
        tempdir = tempfile.mkdtemp()
        linkdir = tempdir + '.link'
        os.symlink(tempdir, linkdir)
        fs = self._make_one(tempfile.tempdir)
        try:
            self.assertTrue(fs.isrealfile(file.name))
            self.assertFalse(fs.isrealfile(link))
            self.assertFalse(fs.isrealfile(tempdir))
            self.assertFalse(fs.isrealfile(linkdir))

            self.assertTrue(fs.isrealdir(tempdir))
            self.assertFalse(fs.isrealdir(linkdir))
            self.assertFalse(fs.isrealdir(file.name))
            self.assertFalse(fs.isrealdir(link))
        finally:
            os.remove(link)
            os.remove(linkdir)
            os.rmdir(tempdir)

    def test_read(self):
        import os
        import tempfile
        f = tempfile.NamedTemporaryFile()
        f.write('hello')
        f.flush()
        fs = self._make_one(os.path.dirname(f.name))
        self.assertEqual(fs.open(f.name).read(), 'hello')
        f.close()


class LogFileTests(unittest2.TestCase):
    def test_iter(self):
        class Fs(object):
                def open(self, path):
                    return """01:47 -!- K-Yo [K-Yo@RZ-853d8549.rez-gif.supelec.fr] has joined #teamrezo
01:47 <ciblout> kage: demain matin, quand tu veux
01:48 * ciblout mange une pomme""".split('\n')

        from rezoirclogs.resources import LogFile
        logfile = LogFile(Fs(), '', '20100409')
        l = list(logfile)
        self.assertEqual(l[0].type, 'status')
        self.assertEqual(l[1].type, 'normal')
        self.assertEqual(l[2].type, 'me')


class ChanTests(unittest2.TestCase):
    def _make_one(self):
        from rezoirclogs.resources import Chan
        fs = DummyFilesystem(files=('/foo/#tagada.20100203.log', '/foo/#tagada.20100204.log'))
        return Chan(fs, '/foo', '#tagada')

    def test_get_item(self):
        from rezoirclogs.resources import LogFile
        from os.path import dirname
        chan = self._make_one()
        date = '20100203'
        logfile = chan[date]
        self.assertIsInstance(logfile, LogFile)
        self.assertEqual(logfile.__name__, date)
        self.assertEqual(logfile.__parent__, chan)
        self.assertEqual(dirname(logfile.path), chan.path)

    def test_iter(self):
        from rezoirclogs.resources import LogFile
        from os.path import dirname
        chan = self._make_one()
        logfiles = list(chan)
        self.assertEqual(len(logfiles), 2)
        for logfile in logfiles:
            self.assertIsInstance(logfile, LogFile)
            self.assertIn(logfile.__name__, ('20100203', '20100204'))
            self.assertEqual(logfile.__parent__, chan)
            self.assertEqual(dirname(logfile.path), chan.path)

    def test_previous_next_chan(self):
        chan = self._make_one()
        first = chan['20100203']
        second = chan['20100204']
        self.assertEqual(first.next.__name__, second.__name__)
        self.assertEqual(first.__name__, second.previous.__name__)

    def test_last(self):
        chan = self._make_one()
        l = chan.last(5)
        self.assertEqual(len(l), 2)
        self.assertEqual(l[0].__name__, '20100204')
        self.assertEqual(l[1].__name__, '20100203')


class DirectoryTests(unittest2.TestCase):
    def _make_one(self):
        from rezoirclogs.resources import Directory
        fs = DummyFilesystem(files=('/foo/#tagada.20100203.log', '/foo/#tagada.20100204.log', '/foo/spam'),
                             dirs=('/foo/bar',))
        return Directory(fs, '/foo')

    def test_get_dir(self):
        from rezoirclogs.resources import Directory
        dir = self._make_one()
        sub = dir['bar']
        self.assertIsInstance(sub, Directory)
        self.assertEqual(sub.path, '/foo/bar')
        self.assertEqual(sub.__name__, 'bar')
        self.assertEqual(sub.__parent__, dir)

    def test_get_chan(self):
        from rezoirclogs.resources import Chan
        dir = self._make_one()
        chan = dir['#tagada']
        self.assertIsInstance(chan, Chan)
        self.assertEqual(chan.path, '/foo')
        self.assertEqual(chan.__name__, '#tagada')
        self.assertEqual(chan.__parent__, dir)

    def test_get_nothing(self):
        dir = self._make_one()
        self.assertRaises(KeyError, dir.__getitem__, 'plonk')
        self.assertRaises(KeyError, dir.__getitem__, 'spa')

    def test_dirs(self):
        from rezoirclogs.resources import Directory
        dir = self._make_one()
        subs = list(dir.dirs)
        self.assertEqual(len(subs), 1)
        sub = subs[0]
        self.assertIsInstance(sub, Directory)
        self.assertEqual(sub.path, '/foo/bar')
        self.assertEqual(sub.__name__, 'bar')
        self.assertEqual(sub.__parent__, dir)

    def test_chans(self):
        from rezoirclogs.resources import Chan
        dir = self._make_one()
        chans = list(dir.chans)
        self.assertEqual(len(chans), 1)
        chan = chans[0]
        self.assertIsInstance(chan, Chan)
        self.assertEqual(chan.path, '/foo')
        self.assertEqual(chan.__name__, '#tagada')
        self.assertEqual(chan.__parent__, dir)

    def test_iter(self):
        dir = self._make_one()
        self.assertEqual(len(list(dir.dirs)), len(list(dir)))


class DummyFilesystem(object):
    import os

    def __init__(self, files=(), dirs=()):
        self.files = files
        self.dirs = dirs

    join = staticmethod(os.path.join)

    def listdir(self, path):
        import os
        return [os.path.basename(f) for f in self.dirs + self.files]

    def isrealfile(self, path):
        return path in self.files

    def isrealdir(self, path):
        return path in self.dirs
