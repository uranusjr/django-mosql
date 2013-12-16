.. image:: https://travis-ci.org/uranusjr/django-mosql.png?branch=master
   :target: https://travis-ci.org/uranusjr/django-mosql

=============
Django MoSQL
=============

Do what Django's ORM can't, without the danger of ``raw``.

-----
Why?
-----

++++++++++++++
Short version
++++++++++++++

Because I want to use raw SQL, but am too lazy to worry about security issues.

+++++++++++++
Long version
+++++++++++++

Django's ORM is cool. And powerful. But ORMs are destined to be leaky, and can't do everything you wish to. That's why Django provides ``raw`` and ``extra`` so that you can roll your own SQL commands if you need to. But with great power comes great responsibility. You lose all the SQL security measures Django provides when you use those methods, and it can be a serious problem unless you are ultra careful.

Enters MoSQL_. MoSQL, in a nutshell, is a tool that generates SQL commands automatically from Python function calls. And it takes care of the injection prevention for you. A perfect match with Django's ``raw``!

All this project does is introduce a Django model manager subclass, and provide an interface to use MoSQL's function calls instead of writing SQL strings yourself. With some syntax sugar, of course.

-------------------------
How do I use this thing?
-------------------------

(Examples in this section are inspired by `this blog post <http://www.xaprb.com/blog/2006/12/07/how-to-select-the-firstleastmax-row-per-group-in-sql/>`_ by Baron Schwartz.)

Let's say you have the following model::

    class Fruit(models.Model):
        kind = models.CharField(max_length=10)
        variety = models.CharField(max_length=10)
        price = models.FloatField()

Then you only need to provide a ``MoManager`` as one of its model managers. Add ``djangomosql`` to your ``INSTALLED_APPS``, and modify the code like this::

    from djangomosql.models import MoManager

    class Fruit(models.Model):
        kind = models.CharField(max_length=10)
        variety = models.CharField(max_length=10)
        price = models.FloatField()

        objects = MoManager()

And you'll be able to generate queries like this::

    from djangomosql.functions import Min

    Fruit.objects.select((Min('price'), 'minprice')).group_by('kind').order_by('-kind')

Which is roughly equivalent to

::

    SELECT fruit.*, MIN(price) as minprice FROM fruit GROUP BY kind ORDER BY kind DESC

Of course, this won't be of much use if we can only do things Django's ORM can. With Django MoSQL, you can achieve many funky things, like::

    m = Fruit.objects
    inner = m.select((Min('price'), 'minprice')).group_by('kind')
    p = m.select().as_('f').order_by('f.kind').join(
        inner, 'x', on={'f.kind': 'x.kind', 'f.price': 'x.minprice'}
    )

Which can be translated into (again, roughly)::

    SELECT f.* FROM fruit AS f INNER JOIN (
        SELECT *, MIN(price) as minprice FROM fruit GROUP BY kind
    ) AS x ON f.kind = x.kind AND f.price = x.minprice

And best of all, you get all the escaping and ORM mapping for free!


--------
LICENSE
--------
BSD 3-cluse license. See the content of file ``LICENSE``.


-----------
Developing
-----------
To run tests, run ``python manage.py test`` inside the test project. You will need ``django-nose`` as well as the dependencies.


.. _MoSQL: http://mosql.mosky.tw/
