from flask import Flask,render_template,request,flash,redirect,url_for
from flask import escape
from flask_sqlalchemy import SQLAlchemy
import os
import sys
import click
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import login_user,login_required,logout_user,current_user

WIN = sys.platform.startswith('win')
if WIN:  # 如果是 Windows 系统，使用三个斜线
    prefix = 'sqlite:///'
else:  # 否则使用四个斜线
    prefix = 'sqlite:////'

app = Flask(__name__)#指定app的名字是什么
app.config['SECRET_KEY'] = 'dev'#设置签名所需的密钥
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控
login_manager = LoginManager(app)#实例化扩展类

# 在扩展类实例化前加载配置
db = SQLAlchemy(app)# 初始化扩展，传入程序实例 app
login_manager.login_view = 'login'# 把 login_manager.login_view 的值设为我们程序的登录视图端点（函数名），则未登录会重定向到登录页面


@app.cli.command()#注册为命令
@click.option('--drop',is_flag=True,help='Create after drop')#设置选项
def initdb(drop):
    """Initialize the database."""
    if drop:#判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo("Initialized database.")#输出提示信息
    '''默认情况下，函数名称就是命令的名字，现在执行 flask initdb 命令就可以创
    建数据库表：'''

@login_manager.user_loader
def load_user(user_id):# 创建用户加载回调函数，接受用户 ID 作为参数
    user = User.query.get(int(user_id))# 用 ID 作为 User 模型的 主键查询对应的用户
    return user# 返回用户对象


class User(db.Model,UserMixin): # 表名将会是 user（自动生成，小写处理），模型类要声明继承 db.Model 。
    id = db.Column(db.Integer, primary_key=True) # 主键，每一个类属性（字段）要实例化 db.Column ，传入的参数为字段的类型
    name = db.Column(db.String(20)) # 名字
    username = db.Column(db.String(20))  # 用户名
    password_hash = db.Column(db.String(128)) #密码散列值

    def set_password(self,password):
        '''
        设置密码的方法
        :param password:接受密码作为参数
        :return:
        '''
        self.password_hash = generate_password_hash(password)#将密码对应的散列值存到password_hash
    def validate_password(self,password):
        '''
        验证密码
        :param password:
        :return:
        '''
        return check_password_hash(self.password_hash,password)
class Movie(db.Model): # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True) # 主键
    title = db.Column(db.String(60)) # 电影标题
    year = db.Column(db.String(4)) # 电影年份


@app.cli.command()
def forge():
    '''生成虚拟数据'''
    db.create_all()#生成表模式

    name = 'Grey Li'
    movies = [
        {'title': 'My Neighbor Totoro', 'year': '1988'},
        {'title': 'Dead Poets Society', 'year': '1989'},
        {'title': 'A Perfect World', 'year': '1993'},
        {'title': 'Leon', 'year': '1994'},
        {'title': 'Mahjong', 'year': '1996'},
        {'title': 'Swallowtail Butterfly', 'year': '1996'},
        {'title': 'King of Comedy', 'year': '1999'},
        {'title': 'Devils on the Doorstep', 'year': '1999'},
        {'title': 'WALL-E', 'year': '2008'},
        {'title': 'The Pork of Music', 'year': '2012'},
    ]
    user = User(name=name)
    db.session.add(user) # 把新创建的记录添加到数据库会话
    for m in movies:
        movie = Movie(title=m['title'],year=m['year'])
        db.session.add(movie)
    db.session.commit()
    click.echo('Done') #

@app.cli.command()#注册为命令
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True,confirmation_prompt=True, help='The password used to login.')
def admin(username,password):
    db.create_all()
    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)# 设置密码
    else:
        click.echo('Creating user...')
        user = User(username=username,name = 'Admin')
        user.set_password(password)
        db.session.add(user)
    db.session.commit()#提交数据库会话
    click.echo('Done.')
'''
使用 app.errorhandler() 装饰器注册一个错误处理函数，它的作用和视图
函数类似，当 404 错误发生时，这个函数会被触发，返回值会作为响应主体返回给
客户端
'''
@app.errorhandler(404)# 传入要处理的错误代码
def page_not_found(e):#接受异常对象作为参数
    user = User.query.first()
    #return render_template('404.html', user=user),404 #返回模板和状态码
    # #上下文函数返回了user,故可以删除user变量的定义,如下所示
    return render_template('404.html'),404

'''
对于多个模板内都需要使用的变量，可以使用 app.context_processor 装饰器注册一个模板上下文处理函数
这个函数返回的变量（以字典键值对的形式）将会统一注入到每一个模板的上下文环境中，因此可以直接在模板中使用。
'''
@app.context_processor
def inject_user():#函数名字可以任意修改
    user = User.query.first()
    return dict(user=user) #需要返回字典，等同于 return {'user':user}

#创建新条目
@app.route('/',methods=['GET','POST'])
def index():#视图函数
    if request.method == 'POST':# 判断是否是post请求
        if not current_user.is_authenticated:# 如果当前用户未认证
            return redirect(url_for(index))# 重定向到主页
        #获取表单数据
        title = request.form.get('title') #传入表单对应输入字段的name值
        year = request.form.get('year') # 传入表单对应输入字段的year值
        #验证数据
        if not title or not year or len(year)>4 or len(title)>60:
            flash('Invalid input.') #显示错误提示
            return redirect(url_for('index'))# 重定向回主页
        #保存表单数据到数据库
        movie = Movie(title=title,year=year)#创建记录
        db.session.add(movie)# 添加到数据库会话
        db.session.commit() #提交数据库会话
        flash('Item created.') #显示成功创建的提示
        return redirect(url_for('index'))# 重定向回主页
    user = User.query.first()
    movies = Movie.query.all()
    return render_template('index.html',user=user,movies=movies)

    #return render_template('index.html',user=user,movies=movies)
    # 上下文函数返回了user,故可以删除user变量的定义,如下所示
    #return render_template('index.html',movies = movies)

#编辑
@app.route('/movie/edit/<int:movie_id>',methods=['GET','POST'])
@login_required #登录保护
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    if request.method=='POST':
        title = request.form.get('title')
        year = request.form.get('year')
        if not title or not year or len(title)>60 or len(year)>4:
            flash('Invalid input.')
            return redirect(url_for('edit',movie_id=movie_id))# 重定向回对应的编辑页面
        movie.title=title # 更新标题
        movie.year=year #更新年份
        db.session.commit()#提交数据库会话
        flash('Item updated')
        return redirect(url_for('index'))#重定向回主页面
    return render_template('edit.html',movie=movie)# 传入被编辑 的电影记录

#删除
@app.route('/movie/edit/delete/<int:movie_id>',methods=['POST'])
@login_required #登录保护
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)# 获取电影记录
    db.session.delete(movie) # 删除对应的记录
    db.session.commit() # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index')) # 重定向回主页

#登录
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))
        user = User.query.first()
        if username == user.username and user.validate_password(password):
            login_user(user)#登入用户
            flash('Login success.')
            return redirect(url_for('index')) #重定向到主页
        flash('Invalid username or password.') # 验证失败，提示错误信息
        return redirect(url_for(login)) # 重定向回登录页面
    return render_template('login.html') #如果不是post则重新渲染登录模板

#设置
@app.route('/settings',methods=['GET','POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']
        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))
        current_user.name = name
        # current_user 会返回当前登录用户的数据库记录对象
        # 等同于下面的用法
        # user = User.query.first()
        # user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))
    return render_template('settings.html')


#登出
@app.route('/logout')
@login_required # 用于视图保护，
def logout():
    logout_user()# 登出用户
    flash('bye~')
    return redirect(url_for('index'))#重定向回首页

















