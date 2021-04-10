import pathlib
import shutil
import subprocess
import zipfile
from io import BytesIO
from typing import AnyStr

import qrcode
from django.conf import settings
from django.template import Context, Template
from django.utils.encoding import force_bytes
from django.utils.translation import activate

from bctip import settings
from bctip.local_settings import WALLET
from core.celery import app
from core.models import CURRENCY_SIGNS, Tip, Wallet, Payment


def odt_template(fn, ctx, page_size="A4"):
    inp = zipfile.ZipFile(fn, "r")
    outs = BytesIO()
    output = zipfile.ZipFile(outs, "a")
    for zi in inp.filelist:
        ext: str = pathlib.Path(zi.filename).suffix
        data: bytes = inp.read(zi.filename)
        if zi.filename == 'content.xml':  # waut for the only interesting file
            # un-escape the quotes (in filters etc.)
            t = Template(data.decode('utf-8').replace('&quot;', '"'))
            data: bytes = force_bytes(t.render(ctx))
        if page_size == "US" and zi.filename == 'styles.xml':
            t = Template(data.decode('utf-8').replace(
                'style:page-layout-properties fo:page-width="297mm" fo:page-height="210.01mm"',
                'style:page-layout-properties fo:page-width="279.4mm" fo:page-height="215.9mm"'))
            data: bytes = force_bytes(t.render(ctx))
        out: AnyStr = data if ext != ".xml" else data.decode('utf-8')
        output.writestr(zi.filename, out)
    output.close()
    content = outs.getvalue()
    return content


# from celery.task.control import inspect
# i = inspect()
# i.scheduled()
# i.active()


@app.task  # (name='tasks.celery_generate_pdf')
def celery_generate_pdf(wallet_id):
    wallet = Wallet.objects.get(id=wallet_id)
    activate(wallet.target_language)
    tips = Tip.objects.filter(wallet=wallet).order_by('id')
    ctx = {'wallet': wallet, 'tips': tips, 'cur_sign': CURRENCY_SIGNS[wallet.divide_currency]}

    unique_tmp = '/tmp/w%s.odt' % wallet.id
    shutil.copyfile(settings.WEBODT_TEMPLATE_PATH + "/" +
                    wallet.template, unique_tmp)
    inpt = zipfile.ZipFile(unique_tmp, "a")
    for tip in tips:
        inpt.writestr("Pictures/%s.png" % tip.id, qrcode_img(tip.get_absolute_url()))
    manifest = Template(inpt.read('META-INF/manifest.xml').decode('utf-8'))
    inpt.writestr("META-INF/manifest.xml", manifest.render(Context(ctx)))
    inpt.close()
    document = odt_template(unique_tmp, Context(ctx))
    document_us = odt_template(unique_tmp, Context(ctx), page_size="US")

    # odt
    fn = settings.PROJECT_DIR + "/static/odt/tips-%s.odt" % wallet.key
    f = open(fn, 'wb')
    f.write(document)
    f.close()

    fn = settings.PROJECT_DIR + "/static/odt/tips-us-%s.odt" % wallet.key
    f = open(fn, 'wb')
    f.write(document_us)
    f.close()

    # pdf
    s = ["unoconv", "-f", "pdf", "-o",
         settings.PROJECT_DIR + "/static/pdf/tips-%s.pdf" % wallet.key,
         settings.PROJECT_DIR + "/static/odt/tips-%s.odt" % wallet.key]
    subprocess.call(s)
    subp = subprocess.Popen(s, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retval = subp.wait()

    s = ["unoconv", "-f", "pdf", "-o",
         settings.PROJECT_DIR + "/static/pdf/tips-us-%s.pdf" % wallet.key,
         settings.PROJECT_DIR + "/static/odt/tips-us-%s.odt" % wallet.key]
    subprocess.call(s)
    subp = subprocess.Popen(s, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retval = subp.wait()

    # png
    s = ["convert", "-density", "300", "-trim",
         settings.PROJECT_DIR + "/static/pdf/tips-%s.pdf" % wallet.key,
         settings.PROJECT_DIR + "/static/png/tips-%s.png" % wallet.key]
    subprocess.call(s)
    subp = subprocess.Popen(s, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retval = subp.wait()

    return True


def qrcode_img(text):
    img = qrcode.make(text, box_size=2, error_correction=qrcode.ERROR_CORRECT_M)
    output = BytesIO()  # StringIO()
    img.save(output, "PNG")
    c = output.getvalue()
    return c


async def invoice_listener():
    async for checking_id in WALLET.paid_invoices_stream():
        invoice_callback_dispatcher(checking_id)


def invoice_callback_dispatcher(checking_id: str):
    try:
        payment = Payment.objects.get(checkint_id=checking_id)
        if payment.is_in:
            print("Payment pending = False")
            payment.pending = False
            payment.save()
    except Payment.DoesNotExist:
        pass
